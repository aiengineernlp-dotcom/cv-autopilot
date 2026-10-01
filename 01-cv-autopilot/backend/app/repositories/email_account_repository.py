"""Couche : Repository -- seul fichier autorisé à faire une requête SQL sur
`email_accounts`. Ne fait jamais : chiffrer/déchiffrer un mot de passe (ça
reste le Service, via core/crypto.py) -- stocke et relit `encrypted_password`
tel quel, une chaîne opaque de son point de vue."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import EmailAccount


async def create(
    db: AsyncSession, *, user_id: uuid.UUID, label: str, imap_host: str, imap_port: int,
    smtp_host: str, smtp_port: int, username: str, encrypted_password: str,
) -> EmailAccount:
    account = EmailAccount(
        user_id=user_id, label=label, imap_host=imap_host, imap_port=imap_port,
        smtp_host=smtp_host, smtp_port=smtp_port, username=username, encrypted_password=encrypted_password,
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


async def list_for_user(db: AsyncSession, user_id: uuid.UUID) -> list[EmailAccount]:
    result = await db.execute(select(EmailAccount).where(EmailAccount.user_id == user_id).order_by(EmailAccount.created_at))
    return list(result.scalars().all())


async def get_owned(db: AsyncSession, *, account_id: uuid.UUID, user_id: uuid.UUID) -> EmailAccount | None:
    result = await db.execute(select(EmailAccount).where(EmailAccount.id == account_id, EmailAccount.user_id == user_id))
    return result.scalar_one_or_none()


async def delete(db: AsyncSession, account: EmailAccount) -> None:
    await db.delete(account)
    await db.commit()
