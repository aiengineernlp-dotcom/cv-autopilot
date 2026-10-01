"""Couche : Router (UI HTTP) -- parse la requête, appelle le Service, sérialise
la réponse. Ne fait jamais : requête SQL, hachage de mot de passe -- tout
passe par auth_service."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.deps import get_current_user
from ..db import get_db
from ..models import User
from ..schemas.auth import LoginRequest, SignupRequest, TokenResponse, UserOut
from ..services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def signup(payload: SignupRequest, db: AsyncSession = Depends(get_db)) -> User:
    try:
        return await auth_service.signup(db, email=payload.email, password=payload.password, full_name=payload.full_name)
    except auth_service.NotInvitedError as e:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(e)) from e
    except auth_service.AuthError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e)) from e


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    try:
        token = await auth_service.login(db, email=payload.email, password=payload.password)
    except auth_service.AuthError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(e)) from e
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
