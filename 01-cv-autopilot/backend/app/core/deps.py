"""Couche : dépendances FastAPI partagées -- session DB par requête, résolution
de l'utilisateur courant depuis le jeton JWT. Utilisé par les Routers,
jamais appelé directement par un Service."""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..db import get_db
from ..models import User
from ..repositories import user_repository
from .security import decode_access_token

bearer_scheme = HTTPBearer()


async def require_admin(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> None:
    """Protège /admin/* -- secret partagé (ADMIN_TOKEN), pas un système de
    rôles complet. Un seul opérateur à ce stade, pas besoin de plus."""
    if not settings.admin_token or credentials.credentials != settings.admin_token:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Non autorisé")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Jeton invalide ou expiré")

    user = await user_repository.get_by_id(db, user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Utilisateur introuvable")

    return user
