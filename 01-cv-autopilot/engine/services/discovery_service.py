"""Couche : Service — orchestrateur.

Fait : trois points d'entrée qui alimentent le même traitement partagé
(_evaluate_postings) — dédoublonnage (Repository seen_postings_repository),
score (Service matching_service), préparation via application_service :
- run() : parcourt la watchlist (Repository discovery_config_repository),
  récupère les offres via les Adapters ATS (Greenhouse, Lever)
- run_from_gmail() : parcourt les comptes Gmail configurés (Repository
  email_accounts_repository), récupère les alertes Indeed ET LinkedIn
  (Adapter gmail_adapter, EMAIL_SOURCES) et les parse (Service
  email_alert_service — un parser différent par source, formats incompatibles)
- run_from_imap() : idem mais pour une boîte mail hébergée n'importe où
  (Repository imap_accounts_repository, Adapter imap_adapter) — mêmes
  sources et parsing, seul le transport change

`max_results` plafonne le nombre d'offres RETENUES (queued), pas le nombre
d'offres examinées — sinon une source bruyante avec beaucoup de rejets
épuiserait le quota avant même d'atteindre les autres sources.

Toujours channel="platform", jamais d'auto-envoi : une offre découverte
(ATS ou alerte email, peu importe la boîte mail) se postule via le lien
d'origine, pas par email direct qu'on connaîtrait — toujours préparée pour
validation humaine.

Ne fait jamais : appeler une API/Adapter directement en dehors de ses points
d'entrée, lire/écrire un fichier lui-même (Repositories), décider d'envoyer
un email (cette décision reste dans application_service, qui refuse de
toute façon puisque channel="platform").
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from ..adapters import gmail_adapter, greenhouse_adapter, imap_adapter, lever_adapter
from ..adapters.posting import Posting
from ..config import ClientConfig
from ..repositories import (
    discovery_config_repository,
    email_accounts_repository,
    imap_accounts_repository,
    roles_repository,
    seen_postings_repository,
)
from . import application_service, email_alert_service, matching_service

FETCHERS = {
    "greenhouse": greenhouse_adapter.fetch,
    "lever": lever_adapter.fetch,
}

# Chaque source email a une syntaxe de requête différente pour Gmail (query
# de recherche complète) et IMAP (juste le sous-texte de l'expéditeur), plus
# son propre parser (formats Indeed et LinkedIn incompatibles entre eux).
EMAIL_SOURCES = [
    {
        "name": "indeed",
        "gmail_query": "from:jobalert.indeed.com",
        "imap_sender": "jobalert.indeed.com",
        "parser": email_alert_service.parse_indeed_alert,
    },
    {
        "name": "linkedin",
        "gmail_query": "from:jobalerts-noreply@linkedin.com",
        "imap_sender": "jobalerts-noreply@linkedin.com",
        "parser": email_alert_service.parse_linkedin_alert,
    },
]


@dataclass
class DiscoveryResult:
    posting: Posting
    score: int
    role_name: str | None
    queued_to: str | None
    skipped_reason: str | None


def _posting_key(posting: Posting) -> str:
    return f"{posting.source}:{posting.external_id}"


def _evaluate_postings(
    client: ClientConfig,
    postings,
    *,
    roles,
    seen: set,
    newly_seen: list,
    results: list,
    min_score: int,
    max_results: int,
    queued_count: int,
    country: str,
) -> int:
    """Dédoublonne, score et prépare une liste d'offres déjà récupérées.
    Retourne le nouveau compteur d'offres retenues."""
    for posting in postings:
        if queued_count >= max_results:
            break

        key = _posting_key(posting)
        if key in seen:
            continue
        seen.add(key)  # évite un doublon intra-passage (même offre vue deux fois avant mark_seen())
        newly_seen.append(key)

        match = matching_service.match(posting.title, posting.description, roles)

        if match.role is None:
            results.append(DiscoveryResult(posting, 0, None, None, "Aucun rôle ne correspond"))
            continue
        if match.score < min_score:
            results.append(DiscoveryResult(posting, match.score, match.role.name, None, "Score sous le seuil"))
            continue

        try:
            app_result = application_service.process(
                client,
                company=posting.company,
                title=posting.title,
                description=posting.description,
                channel="platform",
                country=country,
                recruiter_email=None,
                recruiter_name=None,
                role_id=match.role.id,
                from_email=None,
                send=False,
                force=False,
                notes=f"Découvert automatiquement ({posting.source}) — {posting.url}",
            )
            results.append(DiscoveryResult(posting, match.score, match.role.name, str(app_result.queued_to), None))
            queued_count += 1
        except application_service.ApplicationError as e:
            results.append(DiscoveryResult(posting, match.score, match.role.name, None, str(e)))

    return queued_count


def run(client: ClientConfig, *, min_score: int = 3, max_results: int = 10, country: str = "UAE") -> list[DiscoveryResult]:
    watchlist = discovery_config_repository.load(client)
    seen = seen_postings_repository.load_seen(client)
    roles = roles_repository.load_roles(client)

    results: list[DiscoveryResult] = []
    newly_seen: list[str] = []
    queued_count = 0

    for entry in watchlist:
        if queued_count >= max_results:
            break

        fetcher = FETCHERS.get(entry.provider)
        if fetcher is None:
            results.append(DiscoveryResult(
                Posting(entry.provider, "", entry.company_display_name, "", "", "", ""),
                0, None, None, f"Provider inconnu : {entry.provider}",
            ))
            continue

        try:
            postings = fetcher(entry.board_token, entry.company_display_name)
        except Exception as e:
            results.append(DiscoveryResult(
                Posting(entry.provider, "", entry.company_display_name, "", "", "", ""),
                0, None, None, f"Erreur de récupération : {e}",
            ))
            continue

        queued_count = _evaluate_postings(
            client, postings, roles=roles, seen=seen, newly_seen=newly_seen, results=results,
            min_score=min_score, max_results=max_results, queued_count=queued_count, country=country,
        )

    seen_postings_repository.mark_seen(client, newly_seen)
    return results


def run_from_gmail(client: ClientConfig, *, min_score: int = 3, max_results: int = 10, country: str = "UAE") -> list[DiscoveryResult]:
    accounts = email_accounts_repository.load(client)
    seen = seen_postings_repository.load_seen(client)
    roles = roles_repository.load_roles(client)

    results: list[DiscoveryResult] = []
    newly_seen: list[str] = []
    queued_count = 0

    for account in accounts:
        for source in EMAIL_SOURCES:
            if queued_count >= max_results:
                break

            try:
                messages = gmail_adapter.search_messages(source["gmail_query"], account=account, max_results=50)
            except Exception as e:
                results.append(DiscoveryResult(
                    Posting(source["name"], "", f"(compte {account})", "", "", "", ""),
                    0, None, None, f"Erreur Gmail ({source['name']}) : {e}",
                ))
                continue

            postings = []
            for msg in messages:
                postings.extend(source["parser"](msg["body_text"]))

            queued_count = _evaluate_postings(
                client, postings, roles=roles, seen=seen, newly_seen=newly_seen, results=results,
                min_score=min_score, max_results=max_results, queued_count=queued_count, country=country,
            )

    seen_postings_repository.mark_seen(client, newly_seen)
    return results


def run_from_imap(client: ClientConfig, *, min_score: int = 3, max_results: int = 10, country: str = "UAE") -> list[DiscoveryResult]:
    accounts = imap_accounts_repository.load(client)
    seen = seen_postings_repository.load_seen(client)
    roles = roles_repository.load_roles(client)

    results: list[DiscoveryResult] = []
    newly_seen: list[str] = []
    queued_count = 0

    for account in accounts:
        if queued_count >= max_results:
            break

        password = os.environ.get(f"IMAP_PASSWORD_{account.label.upper()}")
        if not password:
            results.append(DiscoveryResult(
                Posting("email_alert", "", f"(compte {account.label})", "", "", "", ""),
                0, None, None, f"Mot de passe manquant dans .env : IMAP_PASSWORD_{account.label.upper()}",
            ))
            continue

        for source in EMAIL_SOURCES:
            if queued_count >= max_results:
                break

            try:
                messages = imap_adapter.search_messages(
                    source["imap_sender"], host=account.host, port=account.port,
                    username=account.username, password=password, max_results=50,
                )
            except Exception as e:
                results.append(DiscoveryResult(
                    Posting(source["name"], "", f"(compte {account.label})", "", "", "", ""),
                    0, None, None, f"Erreur IMAP ({source['name']}) : {e}",
                ))
                continue

            postings = []
            for msg in messages:
                postings.extend(source["parser"](msg["body_text"]))

            queued_count = _evaluate_postings(
                client, postings, roles=roles, seen=seen, newly_seen=newly_seen, results=results,
                min_score=min_score, max_results=max_results, queued_count=queued_count, country=country,
            )

    seen_postings_repository.mark_seen(client, newly_seen)
    return results
