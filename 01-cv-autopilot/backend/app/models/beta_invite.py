"""Couche : modèle -- liste d'invitation pour la bêta privée (décision produit
du 2026-08-14 : "juste moi et quelques testeurs invités, mais prêt pour le
public à tout moment"). Ne bloque que /auth/signup -- lever la restriction
plus tard (ouverture publique) revient à ne plus vérifier cette table,
sans migration ni changement de schéma."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class BetaInvite(Base):
    __tablename__ = "beta_invites"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    invited_by: Mapped[str | None] = mapped_column(String)
    invited_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())
