"""Couche : Repository -- seul fichier autorisé à faire une requête SQL sur
`cv_uploads`/`cv_upload_extractions`."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import CvUpload, CvUploadExtraction
from ..models.enums import CvUploadStatus


async def create_upload(
    db: AsyncSession, *, user_id: uuid.UUID, file_name: str, storage_key: str, mime_type: str, size_bytes: int,
) -> CvUpload:
    upload = CvUpload(
        user_id=user_id, file_name=file_name, storage_key=storage_key,
        mime_type=mime_type, size_bytes=size_bytes, status=CvUploadStatus.uploaded,
    )
    db.add(upload)
    await db.commit()
    await db.refresh(upload)
    return upload


async def set_status(db: AsyncSession, upload: CvUpload, status: CvUploadStatus) -> None:
    upload.status = status
    await db.commit()


async def save_extraction(db: AsyncSession, *, cv_upload_id: uuid.UUID, raw_extraction: dict) -> CvUploadExtraction:
    extraction = CvUploadExtraction(cv_upload_id=cv_upload_id, raw_extraction=raw_extraction)
    db.add(extraction)
    await db.commit()
    await db.refresh(extraction)
    return extraction


async def list_uploads(db: AsyncSession, user_id: uuid.UUID) -> list[CvUpload]:
    result = await db.execute(select(CvUpload).where(CvUpload.user_id == user_id).order_by(CvUpload.uploaded_at))
    return list(result.scalars().all())


async def count_uploads(db: AsyncSession, user_id: uuid.UUID) -> int:
    return len(await list_uploads(db, user_id))


async def get_upload(db: AsyncSession, upload_id: uuid.UUID) -> CvUpload | None:
    result = await db.execute(select(CvUpload).where(CvUpload.id == upload_id))
    return result.scalar_one_or_none()


async def get_owned_upload(db: AsyncSession, *, upload_id: uuid.UUID, user_id: uuid.UUID) -> CvUpload | None:
    """Comme get_upload, mais filtré par propriétaire -- à utiliser dès qu'un
    upload_id vient du client (delete, etc.). get_upload seul n'était encore
    utilisé nulle part avec un ID fourni par le client, donc l'absence de
    filtre n'avait jamais fuité -- corrigé avant que ce soit le cas (voir
    suppression de CV, 2026-08-15)."""
    result = await db.execute(select(CvUpload).where(CvUpload.id == upload_id, CvUpload.user_id == user_id))
    return result.scalar_one_or_none()


async def delete(db: AsyncSession, upload: CvUpload) -> None:
    """CASCADE côté schéma supprime déjà cv_upload_extractions et
    draft_source_uploads liés -- rien d'autre à faire ici que retirer la ligne."""
    await db.delete(upload)
    await db.commit()


async def delete_all_for_user(db: AsyncSession, user_id: uuid.UUID) -> None:
    """Utilisé par la réinitialisation de profil (2026-08-15). Le Service
    appelant doit avoir déjà supprimé les fichiers physiques (cette fonction
    ne fait que la ligne DB, comme le reste de ce Repository)."""
    await db.execute(CvUpload.__table__.delete().where(CvUpload.user_id == user_id))
    await db.commit()


async def list_extractions_for_uploads(db: AsyncSession, upload_ids: list[uuid.UUID]) -> list[CvUploadExtraction]:
    if not upload_ids:
        return []
    result = await db.execute(select(CvUploadExtraction).where(CvUploadExtraction.cv_upload_id.in_(upload_ids)))
    return list(result.scalars().all())
