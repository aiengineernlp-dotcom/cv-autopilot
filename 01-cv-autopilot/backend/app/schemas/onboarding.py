"""Couche : schémas (contrat HTTP, Pydantic) -- onboarding."""
from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

from pydantic import BaseModel


class CvUploadOut(BaseModel):
    id: uuid.UUID
    file_name: str
    status: str
    uploaded_at: dt.datetime

    model_config = {"from_attributes": True}


class DraftOut(BaseModel):
    id: uuid.UUID
    raw_extraction: dict[str, Any]
    reviewed_extraction: dict[str, Any] | None
    conflicts: list[dict[str, Any]]
    status: str

    model_config = {"from_attributes": True}


class ReviewDraftRequest(BaseModel):
    reviewed_extraction: dict[str, Any]


class RoleTargetRequest(BaseModel):
    name: str


class RoleFromPostingRequest(BaseModel):
    """Adaptation par offre précise (2026-08-15) -- `description` est le
    texte collé par l'utilisateur (ou repris d'une offre de /discovery),
    pas un nom de rôle générique."""

    title: str
    company: str | None = None
    description: str


class CvFileOut(BaseModel):
    version: int
    download_url: str


class RoleOut(BaseModel):
    id: uuid.UUID
    name: str
    summary: str | None
    skills: list[Any]
    keywords: list[str]
    status: str
    coverage_notes: list[str] = []

    model_config = {"from_attributes": True}
