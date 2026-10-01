"""Couche : infrastructure DB — un seul endroit qui sait parler à Postgres.

Fait : crée le moteur async SQLAlchemy et la fabrique de sessions, expose
`Base` (classe déclarative dont héritent tous les modèles) et `get_db`
(dépendance FastAPI qui fournit/ferme une session par requête).
Ne fait jamais : contenir de la logique métier (Services) ni de requête
spécifique à une table (Repositories) — uniquement la plomberie de connexion.
"""
from __future__ import annotations

import datetime as dt
from collections.abc import AsyncGenerator

from sqlalchemy import DateTime
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    # docs/schema.sql utilise TIMESTAMPTZ partout -- sans ce mapping explicite,
    # SQLAlchemy suppose un DateTime naïf par défaut pour `Mapped[datetime]`, ce
    # qui casse dès qu'on lui passe un datetime timezone-aware (bug trouvé en
    # testant /onboarding/draft/confirm le 2026-08-15 : asyncpg refusait
    # confirmed_at avec "can't subtract offset-naive and offset-aware datetimes").
    type_annotation_map = {dt.datetime: DateTime(timezone=True)}


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
