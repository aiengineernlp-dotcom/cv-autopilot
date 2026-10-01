"""Couche : Repository -- seul fichier autorisé à faire une requête SQL sur
`beta_invites`."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import BetaInvite


async def is_invited(db: AsyncSession, email: str) -> bool:
    result = await db.execute(select(BetaInvite.id).where(BetaInvite.email == email))
    return result.scalar_one_or_none() is not None


async def create(db: AsyncSession, *, email: str, invited_by: str | None = None) -> BetaInvite:
    invite = BetaInvite(email=email, invited_by=invited_by)
    db.add(invite)
    await db.commit()
    await db.refresh(invite)
    return invite


async def list_all(db: AsyncSession) -> list[BetaInvite]:
    result = await db.execute(select(BetaInvite).order_by(BetaInvite.invited_at))
    return list(result.scalars().all())


async def delete_by_email(db: AsyncSession, email: str) -> None:
    """Utilisé par la suppression admin d'un compte (2026-08-15) -- sans ça,
    l'email resterait marqué "déjà invité" pour toujours (pas de FK vers
    users -- une invitation existe avant même le signup)."""
    await db.execute(BetaInvite.__table__.delete().where(BetaInvite.email == email))
    await db.commit()
