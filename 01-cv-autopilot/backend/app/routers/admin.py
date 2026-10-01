"""Couche : Router (UI HTTP) -- administration de la bêta privée. Protégé
par require_admin (secret partagé), pas une session utilisateur normale.
Ne fait jamais : logique métier, requête SQL -- délègue au Repository."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.deps import require_admin
from ..db import get_db
from ..repositories import beta_invite_repository
from ..repositories import user_repository
from ..schemas.admin import BetaInviteOut, InviteRequest, UserOut
from ..services import admin_service

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.post("/beta-invites", response_model=BetaInviteOut, status_code=status.HTTP_201_CREATED)
async def invite(payload: InviteRequest, db: AsyncSession = Depends(get_db)) -> BetaInviteOut:
    if await beta_invite_repository.is_invited(db, payload.email):
        raise HTTPException(status.HTTP_409_CONFLICT, "Déjà invité")
    return await beta_invite_repository.create(db, email=payload.email, invited_by="admin")


@router.get("/beta-invites", response_model=list[BetaInviteOut])
async def list_invites(db: AsyncSession = Depends(get_db)):
    return await beta_invite_repository.list_all(db)


@router.get("/users", response_model=list[UserOut])
async def list_users(db: AsyncSession = Depends(get_db)):
    """Liste TOUS les comptes, y compris ceux créés avant le filtre
    d'invitation (absents de GET /admin/beta-invites) -- 2026-08-15,
    pour pouvoir repérer et nettoyer les comptes de test oubliés."""
    return await user_repository.list_all(db)


@router.delete("/users/{email}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(email: str, db: AsyncSession = Depends(get_db)) -> None:
    """Supprime un compte (données + fichiers) -- réservé au nettoyage des
    comptes de test (2026-08-15), protégé par require_admin comme le reste
    de ce router."""
    try:
        await admin_service.delete_user(db, email=email)
    except admin_service.UserNotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e)) from e
