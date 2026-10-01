"""Couche : Repository -- seul fichier autorisé à faire une requête SQL sur
`cv_files`."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import CvFile


async def get_latest(db: AsyncSession, role_id: uuid.UUID) -> CvFile | None:
    result = await db.execute(
        select(CvFile).where(CvFile.role_id == role_id).order_by(CvFile.version.desc()).limit(1)
    )
    return result.scalar_one_or_none()


async def create(db: AsyncSession, *, role_id: uuid.UUID, storage_key: str, version: int) -> CvFile:
    cv_file = CvFile(role_id=role_id, storage_key=storage_key, version=version)
    db.add(cv_file)
    await db.commit()
    await db.refresh(cv_file)
    return cv_file


async def list_for_role(db: AsyncSession, role_id: uuid.UUID) -> list[CvFile]:
    """Utilisé avant la suppression d'un rôle (2026-08-15) -- pour effacer
    les fichiers physiques avant que la ligne DB ne disparaisse en CASCADE."""
    result = await db.execute(select(CvFile).where(CvFile.role_id == role_id))
    return list(result.scalars().all())
