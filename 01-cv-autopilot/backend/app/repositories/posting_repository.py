"""Couche : Repository -- seul fichier autorisé à faire une requête SQL sur
`postings`. La dédup vit dans la contrainte UNIQUE(user_id, source,
external_id) du schéma (voir docs/DATA_MODEL.md) -- `try_create` s'appuie
dessus (INSERT ... ON CONFLICT DO NOTHING) plutôt que de vérifier puis
insérer en deux temps, ce qui éliminerait par construction le bug de
doublon intra-passage trouvé en Phase 1.5 (deux requêtes concurrentes ne
peuvent plus toutes les deux réussir sur la même offre)."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Posting


async def get_by_id(db: AsyncSession, *, posting_id: uuid.UUID, user_id: uuid.UUID) -> Posting | None:
    result = await db.execute(select(Posting).where(Posting.id == posting_id, Posting.user_id == user_id))
    return result.scalar_one_or_none()


async def create_manual(
    db: AsyncSession, *, user_id: uuid.UUID, company: str, title: str, url: str | None, description: str,
) -> Posting:
    """Offre collée manuellement (2026-08-16, voir candidacy_service) --
    contrairement à try_create (dédoublonnage sur `external_id` d'une vraie
    source ATS/email), il n'y a pas d'identifiant externe stable ici : un
    UUID généré sert d'`external_id` pour respecter la contrainte UNIQUE
    (user_id, source, external_id) sans jamais bloquer -- coller deux fois
    la même offre crée volontairement deux candidatures distinctes plutôt
    que d'échouer silencieusement."""
    posting = Posting(
        user_id=user_id, discovery_source_id=None, source="manual", external_id=str(uuid.uuid4()),
        company=company, title=title, location=None, url=url, description=description,
    )
    db.add(posting)
    await db.commit()
    await db.refresh(posting)
    return posting


async def try_create(
    db: AsyncSession, *, user_id: uuid.UUID, discovery_source_id: uuid.UUID, source: str, external_id: str,
    company: str, title: str, location: str, url: str, description: str,
) -> Posting | None:
    """Renvoie la Posting créée, ou None si elle existait déjà (dédup)."""
    stmt = (
        pg_insert(Posting)
        .values(
            user_id=user_id, discovery_source_id=discovery_source_id, source=source, external_id=external_id,
            company=company, title=title, location=location, url=url, description=description,
        )
        .on_conflict_do_nothing(index_elements=["user_id", "source", "external_id"])
        .returning(Posting)
    )
    result = await db.execute(stmt)
    await db.commit()
    row = result.first()
    return row[0] if row else None
