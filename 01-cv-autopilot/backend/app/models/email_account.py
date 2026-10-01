"""Couche : modèle -- comptes email de l'utilisateur (2026-08-16), pour la
découverte par alertes (IMAP) et l'auto-envoi canal email (SMTP, depuis la
propre boîte du candidat). `encrypted_password` n'est jamais lu/déchiffré
ici -- ça reste le travail exclusif de app/core/crypto.py, appelé par le
Service, jamais par ce fichier ni par un Repository."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import ForeignKey, SmallInteger, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class EmailAccount(Base):
    __tablename__ = "email_accounts"
    __table_args__ = (UniqueConstraint("user_id", "label"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    label: Mapped[str] = mapped_column(String, nullable=False)
    imap_host: Mapped[str] = mapped_column(String, nullable=False)
    imap_port: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="993")
    smtp_host: Mapped[str] = mapped_column(String, nullable=False)
    smtp_port: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="465")
    username: Mapped[str] = mapped_column(String, nullable=False)
    encrypted_password: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())
