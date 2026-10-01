"""Couche : Repository -- seul fichier autorisé à faire une requête SQL sur
`extracted_profile_drafts`/`draft_source_uploads`."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import DraftSourceUpload, ExtractedProfileDraft
from ..models.enums import ExtractionStatus


async def get_active_draft(db: AsyncSession, user_id: uuid.UUID) -> ExtractedProfileDraft | None:
    """Un draft par utilisateur, tant qu'il n'est pas confirmé -- une nouvelle
    fusion en écrase le contenu plutôt que d'en créer un deuxième."""
    result = await db.execute(
        select(ExtractedProfileDraft)
        .where(ExtractedProfileDraft.user_id == user_id, ExtractedProfileDraft.status == ExtractionStatus.pending_review)
        .order_by(ExtractedProfileDraft.id.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_confirmed_draft(db: AsyncSession, user_id: uuid.UUID) -> ExtractedProfileDraft | None:
    result = await db.execute(
        select(ExtractedProfileDraft)
        .where(ExtractedProfileDraft.user_id == user_id, ExtractedProfileDraft.status == ExtractionStatus.confirmed)
        .order_by(ExtractedProfileDraft.confirmed_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def upsert_draft(
    db: AsyncSession, *, user_id: uuid.UUID, raw_extraction: dict, conflicts: list, source_upload_ids: list[uuid.UUID],
) -> ExtractedProfileDraft:
    draft = await get_active_draft(db, user_id)
    if draft is None:
        draft = ExtractedProfileDraft(user_id=user_id, raw_extraction=raw_extraction, conflicts=conflicts)
        db.add(draft)
    else:
        draft.raw_extraction = raw_extraction
        draft.conflicts = conflicts
        draft.reviewed_extraction = None  # une nouvelle fusion invalide une relecture précédente

    await db.flush()

    # repart des liens précédents pour ce draft, au cas où une re-fusion change la liste des sources
    await db.execute(DraftSourceUpload.__table__.delete().where(DraftSourceUpload.draft_id == draft.id))
    for upload_id in source_upload_ids:
        db.add(DraftSourceUpload(draft_id=draft.id, cv_upload_id=upload_id))

    await db.commit()
    await db.refresh(draft)
    return draft


async def update_review(db: AsyncSession, draft: ExtractedProfileDraft, reviewed_extraction: dict) -> ExtractedProfileDraft:
    draft.reviewed_extraction = reviewed_extraction
    await db.commit()
    await db.refresh(draft)
    return draft


async def confirm(db: AsyncSession, draft: ExtractedProfileDraft) -> ExtractedProfileDraft:
    draft.status = ExtractionStatus.confirmed
    draft.confirmed_at = dt.datetime.now(dt.timezone.utc)
    await db.commit()
    await db.refresh(draft)
    return draft


async def delete_all_for_user(db: AsyncSession, user_id: uuid.UUID) -> None:
    """Utilisé par la réinitialisation de profil (2026-08-15) -- supprime le
    draft actif ou confirmé, jamais les rôles déjà créés (indépendants,
    voir onboarding_service.reset_profile)."""
    await db.execute(ExtractedProfileDraft.__table__.delete().where(ExtractedProfileDraft.user_id == user_id))
    await db.commit()
