"""Couche : modèle (miroir SQLAlchemy de docs/schema.sql -- sources de
découverte ATS/Gmail/IMAP et offres découvertes). La dédup vit dans la
contrainte UNIQUE de `postings`, pas dans un fichier relu à la main (voir
DATA_MODEL.md -- élimine par construction le bug de doublon intra-passage
trouvé en Phase 1.5).
Ne fait jamais : requête, logique métier -- uniquement la forme des données."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Enum, ForeignKey, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base
from .enums import SourceStatus, SourceType


class DiscoverySource(Base):
    __tablename__ = "discovery_sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[SourceType] = mapped_column(Enum(SourceType, name="source_type", native_enum=True), nullable=False)
    label: Mapped[str] = mapped_column(String, nullable=False)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    credential_ref: Mapped[str | None] = mapped_column(String)  # pointeur vers un secret -- jamais le secret lui-même
    status: Mapped[SourceStatus] = mapped_column(
        Enum(SourceStatus, name="source_status", native_enum=True), nullable=False,
        server_default=SourceStatus.active.value,
    )
    last_run_at: Mapped[datetime | None] = mapped_column()
    last_run_summary: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Posting(Base):
    __tablename__ = "postings"
    __table_args__ = (UniqueConstraint("user_id", "source", "external_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    discovery_source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("discovery_sources.id", ondelete="SET NULL"))
    source: Mapped[str] = mapped_column(String, nullable=False)
    external_id: Mapped[str] = mapped_column(String, nullable=False)
    company: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    location: Mapped[str | None] = mapped_column(String)
    url: Mapped[str | None] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text)
    discovered_at: Mapped[datetime] = mapped_column(server_default=func.now())
