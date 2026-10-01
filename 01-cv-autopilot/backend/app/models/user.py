"""Couche : modèle (miroir SQLAlchemy de docs/schema.sql -- tables `users`, `profiles`).
Ne fait jamais : requête, logique métier -- uniquement la forme des données."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(Text)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    stripe_customer_id: Mapped[str | None] = mapped_column(String)
    plan: Mapped[str] = mapped_column(String, nullable=False, server_default="free")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    profile: Mapped["Profile"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")


class Profile(Base):
    __tablename__ = "profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    headline: Mapped[str | None] = mapped_column(String)
    phone: Mapped[str | None] = mapped_column(String)
    location: Mapped[str | None] = mapped_column(String)
    linkedin_url: Mapped[str | None] = mapped_column(String)
    github_url: Mapped[str | None] = mapped_column(String)
    portfolio_url: Mapped[str | None] = mapped_column(String)
    from_email: Mapped[str | None] = mapped_column(String)
    target_countries: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    education: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    certifications: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now())

    user: Mapped[User] = relationship(back_populates="profile")
