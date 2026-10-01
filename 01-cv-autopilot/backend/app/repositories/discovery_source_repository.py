"""Couche : Repository -- seul fichier autorisé à faire une requête SQL sur
`discovery_sources`."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import DiscoverySource
from ..models.enums import SourceType


async def create(
    db: AsyncSession, *, user_id: uuid.UUID, type_: SourceType, label: str, config: dict, credential_ref: str | None = None,
) -> DiscoverySource:
    source = DiscoverySource(user_id=user_id, type=type_, label=label, config=config, credential_ref=credential_ref)
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return source


async def list_active(db: AsyncSession, user_id: uuid.UUID, *, type_: SourceType | None = None) -> list[DiscoverySource]:
    query = select(DiscoverySource).where(DiscoverySource.user_id == user_id, DiscoverySource.status == "active")
    if type_ is not None:
        query = query.where(DiscoverySource.type == type_)
    result = await db.execute(query.order_by(DiscoverySource.created_at))
    return list(result.scalars().all())


async def list_all(db: AsyncSession, user_id: uuid.UUID) -> list[DiscoverySource]:
    result = await db.execute(select(DiscoverySource).where(DiscoverySource.user_id == user_id).order_by(DiscoverySource.created_at))
    return list(result.scalars().all())


async def record_run(db: AsyncSession, source: DiscoverySource, *, summary: dict, status: str = "active") -> None:
    source.last_run_at = dt.datetime.now(dt.timezone.utc)
    source.last_run_summary = summary
    source.status = status
    await db.commit()
