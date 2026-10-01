"""Couche : schémas (contrat HTTP, Pydantic) -- ce que l'API accepte/renvoie,
jamais les modèles SQLAlchemy exposés directement."""
from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=1)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    plan: str

    model_config = {"from_attributes": True}
