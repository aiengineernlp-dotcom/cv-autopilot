"""Couche : Service -- gestion des comptes email de l'utilisateur (2026-08-16).
Seul endroit qui déchiffre un mot de passe pour l'utiliser réellement (test
de connexion, lecture IMAP, envoi SMTP) -- jamais renvoyé en clair au Router,
jamais journalisé.
Ne fait jamais : requête SQL directe (délègue à email_account_repository),
appeler imaplib/smtplib directement (délègue aux Adapters)."""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from ..adapters import imap_adapter
from ..core import crypto
from ..models import EmailAccount
from ..repositories import email_account_repository


class EmailAccountError(RuntimeError):
    """Erreur métier (connexion IMAP échouée...) -- jamais une exception technique brute."""


class EmailAccountNotFoundError(EmailAccountError):
    """Distincte pour que le Router la mappe en 404."""


async def connect(
    db: AsyncSession, *, user_id: uuid.UUID, label: str, imap_host: str, imap_port: int,
    smtp_host: str, smtp_port: int, username: str, password: str,
) -> EmailAccount:
    """Vérifie la connexion IMAP AVANT d'enregistrer -- un mot de passe ou un
    host invalide échoue immédiatement (message clair) plutôt que d'être
    stocké silencieusement et de casser à la première utilisation réelle."""
    try:
        imap_adapter.search_messages(
            "no-such-sender-just-testing-the-connection", host=imap_host, port=imap_port,
            username=username, password=password, max_results=1,
        )
    except imap_adapter.ImapError as e:
        raise EmailAccountError(f"Connexion IMAP impossible -- vérifie l'hôte, le port et le mot de passe : {e}") from e

    encrypted = crypto.encrypt_secret(password)
    return await email_account_repository.create(
        db, user_id=user_id, label=label, imap_host=imap_host, imap_port=imap_port,
        smtp_host=smtp_host, smtp_port=smtp_port, username=username, encrypted_password=encrypted,
    )


async def list_accounts(db: AsyncSession, user_id: uuid.UUID) -> list[EmailAccount]:
    return await email_account_repository.list_for_user(db, user_id)


async def get_owned_account(db: AsyncSession, *, account_id: uuid.UUID, user_id: uuid.UUID) -> EmailAccount:
    account = await email_account_repository.get_owned(db, account_id=account_id, user_id=user_id)
    if account is None:
        raise EmailAccountNotFoundError("Compte email introuvable")
    return account


async def delete_account(db: AsyncSession, *, account_id: uuid.UUID, user_id: uuid.UUID) -> None:
    account = await get_owned_account(db, account_id=account_id, user_id=user_id)
    await email_account_repository.delete(db, account)


def decrypt_password(account: EmailAccount) -> str:
    """Le seul point d'entrée pour obtenir le mot de passe en clair -- appelé
    uniquement au moment d'agir réellement (lecture IMAP, envoi SMTP), jamais
    pour l'exposer via une réponse HTTP."""
    return crypto.decrypt_secret(account.encrypted_password)
