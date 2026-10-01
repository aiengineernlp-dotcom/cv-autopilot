"""Couche : Service -- crée une candidature trackable depuis une offre
collée manuellement (2026-08-16). Comble un écart trouvé en testant 10
postes différents (voir backend/scripts/personas/) : `POST
/onboarding/roles/from-posting` adapte déjà le CV vers une offre précise,
mais ne crée jamais de Posting/Application -- une candidature venue de la
découverte automatique (discovery_service) est trackable (lettre, statut,
envoi), une adaptée manuellement ne l'était pas, sans contournement SQL.

Fait : à partir d'un rôle déjà créé (par `create_role_from_posting`) et du
texte de l'offre correspondante, crée le Posting + l'Application en file
(canal plateforme, statut "queued" -- même canal par défaut qu'une
découverte automatique, jamais d'auto-envoi tant que l'utilisateur n'a
pas lui-même fourni l'email d'un recruteur, voir application_send_service).
Ne fait jamais : adapter le rôle (onboarding_service.create_role_from_posting,
à appeler avant), générer le CV (cv_generation_service), écrire en base
directement (délègue aux Repositories)."""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Application
from ..repositories import application_repository, posting_repository, role_repository


class CandidacyError(RuntimeError):
    """Erreur métier (rôle introuvable ou appartenant à un autre utilisateur)
    -- jamais une exception technique brute."""


async def create_from_posting(
    db: AsyncSession, *, user_id: uuid.UUID, role_id: uuid.UUID,
    company: str, title: str, description: str, url: str | None,
) -> Application:
    role = await role_repository.get_role(db, role_id=role_id, user_id=user_id)
    if role is None:
        raise CandidacyError("Rôle introuvable -- crée-le d'abord via POST /onboarding/roles/from-posting")

    posting = await posting_repository.create_manual(
        db, user_id=user_id, company=company, title=title, url=url, description=description,
    )
    return await application_repository.create_queued(
        db, user_id=user_id, posting_id=posting.id, role_id=role_id, company=company, title=title,
        match_score=None, notes="Candidature créée depuis une offre collée manuellement.",
    )
