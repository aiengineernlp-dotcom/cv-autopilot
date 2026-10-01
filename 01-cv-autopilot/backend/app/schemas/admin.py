"""Couche : schémas (contrat HTTP, Pydantic) -- administration de la bêta."""
from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, EmailStr


class InviteRequest(BaseModel):
    email: EmailStr


class BetaInviteOut(BaseModel):
    email: str
    invited_at: dt.datetime

    model_config = {"from_attributes": True}


class UserOut(BaseModel):
    email: str
    full_name: str
    plan: str
    created_at: dt.datetime

    model_config = {"from_attributes": True}
