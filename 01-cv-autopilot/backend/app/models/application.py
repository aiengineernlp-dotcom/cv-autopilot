"""Couche : modèle (miroir SQLAlchemy de docs/schema.sql -- table `applications`,
remplace tracker-candidatures.md + le dossier queue/ de la Phase 1).
Ne fait jamais : requête, logique métier -- uniquement la forme des données."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Enum, ForeignKey, SmallInteger, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base
from .enums import ApplicationStatus, ChannelType


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    posting_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("postings.id", ondelete="SET NULL"))
    role_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="SET NULL"))
    cv_file_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("cv_files.id", ondelete="SET NULL"))
    company: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    channel: Mapped[ChannelType] = mapped_column(Enum(ChannelType, name="channel_type", native_enum=True), nullable=False)
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, name="application_status", native_enum=True), nullable=False,
        server_default=ApplicationStatus.queued.value,
    )
    match_score: Mapped[int | None] = mapped_column(SmallInteger)
    recruiter_email: Mapped[str | None] = mapped_column(String)
    recruiter_name: Mapped[str | None] = mapped_column(String)
    cover_letter_text: Mapped[str | None] = mapped_column(Text)  # figée au moment de l'envoi, jamais régénérée
    storage_key: Mapped[str | None] = mapped_column(String)
    notes: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column()
    follow_up_due_at: Mapped[datetime | None] = mapped_column()
    follow_up_sent_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now())
