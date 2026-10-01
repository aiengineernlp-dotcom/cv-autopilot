"""Couche : Service -- envoi réel d'une candidature par email (2026-08-16),
canal direct uniquement (voir PRODUCT.md "Niveau d'autonomie" : jamais
d'auto-envoi sur canal plateforme -- une offre découverte automatiquement
reste "à valider toi-même sur le lien d'origine", cette brique ne
s'applique qu'une fois qu'un vrai email de recruteur existe, fourni
explicitement par l'utilisateur). Assemble le CV déjà généré
(cv_generation_service) + la lettre déjà générée (cover_letter_service) +
la connexion SMTP de l'utilisateur (email_account_service) et délègue
l'envoi à smtp_adapter.
Ne fait jamais : générer la lettre ou le CV lui-même (l'appelant doit les
avoir déjà produits), écrire en base directement (délègue à
application_repository), garder un mot de passe déchiffré au-delà de cet
appel."""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from ..adapters import smtp_adapter
from ..core import storage
from ..core.crypto import CryptoNotConfiguredError
from ..repositories import application_repository, cv_file_repository, email_account_repository, user_repository
from . import email_account_service


class ApplicationSendError(RuntimeError):
    """Erreur métier (candidature/CV/lettre manquants, déjà envoyée, SMTP en
    échec...) -- jamais une exception technique brute."""


class ApplicationSendNotFoundError(ApplicationSendError):
    """Distincte pour que le Router la mappe en 404 plutôt qu'en 400."""


async def send(
    db: AsyncSession, *, user_id: uuid.UUID, application_id: uuid.UUID, email_account_id: uuid.UUID,
    recruiter_email: str, recruiter_name: str | None, dry_run: bool,
) -> dict:
    """dry_run=True (toujours le premier appel côté UI, voir smtp_adapter) :
    construit et renvoie l'aperçu exact de ce qui serait envoyé, aucune
    connexion SMTP ouverte, rien écrit en base. dry_run=False : envoie
    réellement et fige la candidature (application_repository.mark_sent)."""
    app = await application_repository.get_owned(db, application_id=application_id, user_id=user_id)
    if app is None:
        raise ApplicationSendNotFoundError("Candidature introuvable")
    if app.sent_at is not None:
        raise ApplicationSendError("Candidature déjà envoyée -- impossible de renvoyer")
    if not app.cover_letter_text:
        raise ApplicationSendError("Génère d'abord la lettre de motivation (POST .../cover-letter)")
    if app.role_id is None:
        raise ApplicationSendError("Candidature sans rôle associé -- aucun CV à joindre")

    cv_file = await cv_file_repository.get_latest(db, app.role_id)
    if cv_file is None:
        raise ApplicationSendError("Génère d'abord le CV pour ce rôle (POST /roles/{id}/generate-cv)")

    account = await email_account_repository.get_owned(db, account_id=email_account_id, user_id=user_id)
    if account is None:
        raise ApplicationSendNotFoundError("Compte email introuvable")

    user = await user_repository.get_by_id(db, user_id)
    subject = f"Application — {app.title} | {user.full_name}"
    attachment_path = storage.generated_file_path(cv_file.storage_key)

    if dry_run:
        password = ""  # jamais déchiffré pour un simple aperçu -- aucune connexion SMTP n'est ouverte
    else:
        try:
            password = email_account_service.decrypt_password(account)
        except CryptoNotConfiguredError as e:
            raise ApplicationSendError(str(e)) from e

    try:
        result = smtp_adapter.send(
            host=account.smtp_host, port=account.smtp_port, username=account.username, password=password,
            from_email=account.username, to=recruiter_email, subject=subject, text=app.cover_letter_text,
            attachment_path=attachment_path, dry_run=dry_run,
        )
    except smtp_adapter.SmtpError as e:
        raise ApplicationSendError(str(e)) from e

    if not dry_run:
        app = await application_repository.mark_sent(
            db, app, cv_file_id=cv_file.id, recruiter_email=recruiter_email, recruiter_name=recruiter_name,
        )

    return {"dry_run": dry_run, "preview": result.get("preview"), "application": app}
