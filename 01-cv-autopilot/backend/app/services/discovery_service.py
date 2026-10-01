"""Couche : Service -- orchestrateur de la découverte automatique (Phase 1.5
portée au web, 2026-08-15 pour les sources ATS ; alertes email ajoutées le
2026-08-16). Port de ../engine/services/discovery_service.py. Gmail reste
CLI-only (flux OAuth par utilisateur pas construit côté web) ; IMAP est
construit -- une source de type `imap` référence un `email_accounts.id`
déjà connecté (voir email_account_service), le mot de passe est déchiffré
juste avant l'appel IMAP, jamais persisté en clair ni journalisé.

Fait : pour chaque source active d'un utilisateur (ATS ou alerte email),
récupère les offres, dédoublonne (contrainte UNIQUE de `postings`, voir
posting_repository), score contre TOUS les rôles de l'utilisateur
(matching_service), crée une candidature "queued" (canal plateforme --
jamais d'auto-envoi, voir PRODUCT.md "Niveau d'autonomie") pour chaque
offre au-dessus du seuil.
Ne fait jamais : appeler un Adapter en dehors de ce point d'entrée, écrire
en base directement (délègue aux Repositories), décider d'envoyer un email
(cette décision n'existe même pas pour le canal plateforme -- une offre
trouvée par alerte email reste "à valider toi-même sur le lien d'origine",
exactement comme une offre ATS)."""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from ..adapters import greenhouse_adapter, imap_adapter, lever_adapter
from ..adapters.posting import Posting
from ..core.crypto import CryptoNotConfiguredError
from ..models.enums import SourceType
from ..repositories import (
    application_repository,
    discovery_source_repository,
    email_account_repository,
    posting_repository,
    role_repository,
)
from . import email_account_service, email_alert_service, matching_service

FETCHERS = {
    SourceType.ats_greenhouse: greenhouse_adapter.fetch,
    SourceType.ats_lever: lever_adapter.fetch,
}

# Chaque source d'alerte a son propre expéditeur à chercher en IMAP et son
# propre parser (formats Indeed et LinkedIn incompatibles entre eux) --
# même table que engine/services/discovery_service.py::EMAIL_SOURCES.
EMAIL_ALERT_SOURCES = [
    {"name": "indeed_alert", "imap_sender": "jobalert.indeed.com", "parser": email_alert_service.parse_indeed_alert},
    {"name": "linkedin_alert", "imap_sender": "jobalerts-noreply@linkedin.com", "parser": email_alert_service.parse_linkedin_alert},
]

DEFAULT_MIN_SCORE = 3  # même seuil que Phase 1 (engine/services/discovery_service.py)


async def _process_postings(
    db: AsyncSession, *, user_id: uuid.UUID, source, postings: list[Posting], roles, min_score: int,
) -> tuple[int, int]:
    """Partagé par toutes les sources (ATS et alerte email) -- dédoublonnage,
    score, mise en file. Retourne (nouvelles offres, mises en file)."""
    new_count, queued_count = 0, 0
    for posting in postings:
        created = await posting_repository.try_create(
            db, user_id=user_id, discovery_source_id=source.id, source=posting.source,
            external_id=posting.external_id, company=posting.company, title=posting.title,
            location=posting.location, url=posting.url, description=posting.description,
        )
        if created is None:
            continue  # déjà vue lors d'un passage précédent

        new_count += 1
        match = matching_service.match(posting.title, posting.description, roles)
        if match.role is not None and match.score >= min_score:
            await application_repository.create_queued(
                db, user_id=user_id, posting_id=created.id, role_id=match.role.id,
                company=posting.company, title=posting.title, match_score=match.score,
                notes=f"Découvert automatiquement ({posting.source}) — {posting.url}",
            )
            queued_count += 1
    return new_count, queued_count


async def run(db: AsyncSession, *, user_id: uuid.UUID, min_score: int = DEFAULT_MIN_SCORE) -> dict:
    all_sources = await discovery_source_repository.list_active(db, user_id)
    ats_sources = [s for s in all_sources if s.type in FETCHERS]
    email_sources = [s for s in all_sources if s.type == SourceType.imap]
    roles = await role_repository.list_roles(db, user_id)

    summary = {
        "sources_checked": len(ats_sources) + len(email_sources),
        "postings_found": 0, "new_postings": 0, "queued": 0, "errors": [],
    }

    if not roles:
        summary["errors"].append("Aucun rôle confirmé -- termine l'onboarding avant de lancer la recherche.")
        return summary

    for source in ats_sources:
        fetcher = FETCHERS[source.type]
        board_token = source.config.get("board_token", "")
        company_display_name = source.config.get("company_display_name", source.label)

        try:
            postings = fetcher(board_token, company_display_name)
        except Exception as e:  # erreur réseau/API tierce -- ne bloque pas les autres sources
            summary["errors"].append(f"{source.label} : {e}")
            await discovery_source_repository.record_run(db, source, summary={"error": str(e)}, status="error")
            continue

        summary["postings_found"] += len(postings)
        source_new, source_queued = await _process_postings(
            db, user_id=user_id, source=source, postings=postings, roles=roles, min_score=min_score,
        )
        summary["new_postings"] += source_new
        summary["queued"] += source_queued
        await discovery_source_repository.record_run(
            db, source, summary={"found": len(postings), "new": source_new, "queued": source_queued}
        )

    for source in email_sources:
        account_id = source.config.get("email_account_id")
        account = await email_account_repository.get_owned(
            db, account_id=uuid.UUID(account_id), user_id=user_id,
        ) if account_id else None

        if account is None:
            summary["errors"].append(f"{source.label} : compte email introuvable (supprimé ?)")
            await discovery_source_repository.record_run(
                db, source, summary={"error": "compte email introuvable"}, status="error",
            )
            continue

        try:
            password = email_account_service.decrypt_password(account)
        except CryptoNotConfiguredError as e:
            # Ne doit jamais planter tout le run() -- une source cassée
            # (donnée corrompue, clé de chiffrement changée) reste isolée,
            # les autres sources (ATS, autres comptes email) continuent.
            summary["errors"].append(f"{source.label} : {e}")
            await discovery_source_repository.record_run(db, source, summary={"error": str(e)}, status="error")
            continue

        postings: list[Posting] = []
        alert_errors: list[str] = []

        for alert_source in EMAIL_ALERT_SOURCES:
            try:
                messages = imap_adapter.search_messages(
                    alert_source["imap_sender"], host=account.imap_host, port=account.imap_port,
                    username=account.username, password=password, max_results=50,
                )
            except imap_adapter.ImapError as e:
                alert_errors.append(f"{alert_source['name']} : {e}")
                continue
            for msg in messages:
                postings.extend(alert_source["parser"](msg["body_text"]))

        if alert_errors and not postings:
            summary["errors"].append(f"{source.label} : {'; '.join(alert_errors)}")
            await discovery_source_repository.record_run(
                db, source, summary={"error": "; ".join(alert_errors)}, status="error",
            )
            continue

        summary["postings_found"] += len(postings)
        source_new, source_queued = await _process_postings(
            db, user_id=user_id, source=source, postings=postings, roles=roles, min_score=min_score,
        )
        summary["new_postings"] += source_new
        summary["queued"] += source_queued
        await discovery_source_repository.record_run(
            db, source, summary={"found": len(postings), "new": source_new, "queued": source_queued}
        )

    return summary
