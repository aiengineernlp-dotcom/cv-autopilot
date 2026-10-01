"""Couche : modèle (miroir SQLAlchemy de docs/schema.sql -- expériences, rôles,
projets, CV générés). Voir DATA_MODEL.md : un même poste, raconté différemment
selon le rôle ciblé -- `experiences` est partagé, `role_experience_bullets` varie.
Ne fait jamais : requête, logique métier -- uniquement la forme des données."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, SmallInteger, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class Experience(Base):
    __tablename__ = "experiences"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    position_title: Mapped[str] = mapped_column(String, nullable=False)
    company_location: Mapped[str] = mapped_column(String, nullable=False)
    date_range: Mapped[str] = mapped_column(String, nullable=False)
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")


class Role(Base):
    __tablename__ = "roles"
    __table_args__ = (UniqueConstraint("user_id", "name"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    keywords: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    summary: Mapped[str | None] = mapped_column(Text)
    skills: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    cover_letter_template: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, nullable=False, server_default="draft")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class RoleExperienceBullet(Base):
    __tablename__ = "role_experience_bullets"

    role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    experience_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("experiences.id", ondelete="CASCADE"), primary_key=True)
    bullets: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")


class RoleProject(Base):
    __tablename__ = "role_projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    subtitle: Mapped[str | None] = mapped_column(String)
    year: Mapped[str | None] = mapped_column(String)
    bullets: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")


class CvFile(Base):
    __tablename__ = "cv_files"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    storage_key: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    generated_at: Mapped[datetime] = mapped_column(server_default=func.now())
