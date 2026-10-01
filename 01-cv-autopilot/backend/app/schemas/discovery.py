"""Couche : schémas (contrat HTTP, Pydantic) -- découverte automatique."""
from __future__ import annotations

import datetime as dt
import uuid
from typing import Any, Literal

from pydantic import BaseModel, EmailStr


class KnownCompanyOut(BaseModel):
    label: str
    type: Literal["ats_greenhouse", "ats_lever"]
    board_token: str


class AddSourceRequest(BaseModel):
    type: Literal["ats_greenhouse", "ats_lever"]
    label: str  # nom affiché de l'entreprise, ex: "Stripe"
    board_token: str  # trouvé dans l'URL du board carrière -- voir frontend/README.md


class AddEmailAlertSourceRequest(BaseModel):
    """Découverte par alertes email (2026-08-16) -- distincte de
    AddSourceRequest plutôt que des champs optionnels partagés : un
    board_token et un email_account_id n'ont rien en commun, les mélanger
    dans un seul schéma aurait rendu les deux à moitié valides tout le
    temps."""

    email_account_id: uuid.UUID


class DiscoverySourceOut(BaseModel):
    id: uuid.UUID
    type: str
    label: str
    status: str
    last_run_at: dt.datetime | None
    last_run_summary: dict[str, Any] | None

    model_config = {"from_attributes": True}


class RunDiscoveryResponse(BaseModel):
    sources_checked: int
    postings_found: int
    new_postings: int
    queued: int
    errors: list[str]


class CreateCandidacyFromPostingRequest(BaseModel):
    """Comble l'écart trouvé en testant 10 postes (2026-08-16) : un rôle créé
    depuis une offre collée (POST /onboarding/roles/from-posting) n'avait
    nulle part où accrocher une lettre ou un envoi -- role_id doit référencer
    un rôle déjà créé par cet endpoint. url optionnel : une offre partagée
    par un ami ou vue sur une affiche n'a pas toujours de lien."""

    role_id: uuid.UUID
    company: str
    title: str
    description: str
    url: str | None = None


class ApplicationOut(BaseModel):
    id: uuid.UUID
    company: str
    title: str
    channel: str
    status: str
    match_score: int | None
    notes: str | None
    posting_url: str | None = None  # absent sur le modèle Application -- toujours fourni via model_copy() par le Router (voir routers/discovery.py) ; le défaut évite l'échec de model_validate() sur un objet Application qui n'a pas cet attribut
    cover_letter_text: str | None
    sent_at: dt.datetime | None
    created_at: dt.datetime

    model_config = {"from_attributes": True}


ApplicationStatusLiteral = Literal[
    "queued", "sent", "viewed", "contacted", "interview_scheduled", "offer_received", "rejected",
]


class UpdateApplicationStatusRequest(BaseModel):
    status: ApplicationStatusLiteral


class UpdateCoverLetterRequest(BaseModel):
    """Édition manuelle de la lettre après génération (2026-08-16) -- l'IA
    propose un premier jet, l'utilisateur reste toujours libre de le
    corriger avant l'envoi. Même règle que la génération : refusé une fois
    la candidature envoyée (voir routers/discovery.py)."""

    cover_letter_text: str


class SendApplicationRequest(BaseModel):
    """Envoi réel canal email (2026-08-16) -- l'email du recruteur est
    toujours fourni explicitement par l'utilisateur, jamais deviné :
    `applications.recruiter_email` reste vide tant qu'aucun envoi direct n'a
    eu lieu (voir docs/schema.sql), une candidature découverte automatiquement
    n'a jamais de contact direct connu."""

    email_account_id: uuid.UUID
    recruiter_email: EmailStr
    recruiter_name: str | None = None
    confirm: bool = False  # False (défaut) = aperçu seul, aucune connexion SMTP ; True = envoi réel


class SendApplicationPreview(BaseModel):
    """Champs renommés depuis le dict brut de smtp_adapter (qui utilise la
    clé "from", un mot réservé Python) -- construit explicitement par le
    Router, jamais par model_validate() direct sur ce dict."""

    sender: str
    to: str
    subject: str
    text: str
    attachment: str | None


class SendApplicationResponse(BaseModel):
    dry_run: bool
    preview: SendApplicationPreview | None = None
    application: ApplicationOut | None = None  # présent seulement si dry_run=False (envoi réel réussi)
