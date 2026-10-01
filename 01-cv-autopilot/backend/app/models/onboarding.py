"""Couche : modèle (miroir SQLAlchemy de docs/schema.sql -- upload + extraction
+ relecture obligatoire + fusion multi-CV, voir docs/DATA_MODEL.md).
Ne fait jamais : requête, logique métier -- uniquement la forme des données."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Enum, ForeignKey, Integer, String, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base
from .enums import CvUploadStatus, ExtractionStatus


class CvUpload(Base):
    __tablename__ = "cv_uploads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    file_name: Mapped[str] = mapped_column(String, nullable=False)
    storage_key: Mapped[str] = mapped_column(String, nullable=False)
    mime_type: Mapped[str] = mapped_column(String, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[CvUploadStatus] = mapped_column(
        Enum(CvUploadStatus, name="cv_upload_status", native_enum=True), nullable=False,
        server_default=CvUploadStatus.uploaded.value,
    )
    uploaded_at: Mapped[datetime] = mapped_column(server_default=func.now())


class CvUploadExtraction(Base):
    """Une ligne par upload -- sortie brute de la brique 1 (extraction),
    inchangée. Voir prototypes/cv-extraction/."""

    __tablename__ = "cv_upload_extractions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    cv_upload_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cv_uploads.id", ondelete="CASCADE"), nullable=False)
    raw_extraction: Mapped[dict] = mapped_column(JSONB, nullable=False)
    extracted_at: Mapped[datetime] = mapped_column(server_default=func.now())


class ExtractedProfileDraft(Base):
    """LA vue fusionnée (brique fusion, voir prototypes/cv-merge/) que
    l'utilisateur relit -- un seul draft par utilisateur, même si plusieurs
    CV ont été uploadés. `conflicts` porte les désaccords entre documents
    sources, jamais tranchés automatiquement (voir DATA_MODEL.md)."""

    __tablename__ = "extracted_profile_drafts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    raw_extraction: Mapped[dict] = mapped_column(JSONB, nullable=False)
    reviewed_extraction: Mapped[dict | None] = mapped_column(JSONB)
    conflicts: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    status: Mapped[ExtractionStatus] = mapped_column(
        Enum(ExtractionStatus, name="extraction_status", native_enum=True), nullable=False,
        server_default=ExtractionStatus.pending_review.value,
    )
    confirmed_at: Mapped[datetime | None] = mapped_column()


class DraftSourceUpload(Base):
    """Traçabilité : quels uploads ont nourri quel draft fusionné."""

    __tablename__ = "draft_source_uploads"

    draft_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("extracted_profile_drafts.id", ondelete="CASCADE"), primary_key=True)
    cv_upload_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cv_uploads.id", ondelete="CASCADE"), primary_key=True)
