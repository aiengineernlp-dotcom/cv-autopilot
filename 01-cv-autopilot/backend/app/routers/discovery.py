"""Couche : Router (UI HTTP) -- découverte automatique. Parse la requête,
appelle discovery_service, sérialise. Ne fait jamais : appeler un Adapter
ATS, requête SQL -- tout passe par le Service/Repository."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.deps import get_current_user
from ..data.known_companies import KNOWN_COMPANIES
from ..db import get_db
from ..models import User
from ..models.enums import ApplicationStatus, SourceType
from ..repositories import application_repository, discovery_source_repository
from ..schemas.discovery import (
    AddEmailAlertSourceRequest,
    AddSourceRequest,
    ApplicationOut,
    CreateCandidacyFromPostingRequest,
    DiscoverySourceOut,
    KnownCompanyOut,
    RunDiscoveryResponse,
    SendApplicationPreview,
    SendApplicationRequest,
    SendApplicationResponse,
    UpdateApplicationStatusRequest,
    UpdateCoverLetterRequest,
)
from ..services import application_send_service, candidacy_service, cover_letter_service, discovery_service, email_account_service

router = APIRouter(prefix="/discovery", tags=["discovery"])


def _to_application_out(app, posting_url: str | None) -> ApplicationOut:
    return ApplicationOut.model_validate(app).model_copy(update={"posting_url": posting_url})

_TYPE_MAP = {"ats_greenhouse": SourceType.ats_greenhouse, "ats_lever": SourceType.ats_lever}


@router.get("/known-companies", response_model=list[KnownCompanyOut])
async def list_known_companies(current_user: User = Depends(get_current_user)):
    """Liste de départ vérifiée (2026-08-15, voir app/data/known_companies.py)
    -- laisse choisir une entreprise par nom plutôt que d'exiger de deviner
    le type ATS et le board token. N'exclut pas l'ajout manuel."""
    return KNOWN_COMPANIES


@router.post("/sources", response_model=DiscoverySourceOut, status_code=201)
async def add_source(
    payload: AddSourceRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> DiscoverySourceOut:
    source = await discovery_source_repository.create(
        db, user_id=current_user.id, type_=_TYPE_MAP[payload.type], label=payload.label,
        config={"board_token": payload.board_token, "company_display_name": payload.label},
    )
    return source


@router.post("/sources/email-alerts", response_model=DiscoverySourceOut, status_code=201)
async def add_email_alert_source(
    payload: AddEmailAlertSourceRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> DiscoverySourceOut:
    """Découverte par alertes email (2026-08-16) -- une source par compte
    email connecté, cherche les alertes Indeed/LinkedIn dedans (voir
    discovery_service.EMAIL_ALERT_SOURCES). Le compte doit déjà exister et
    appartenir à l'utilisateur (voir POST /email-accounts)."""
    try:
        account = await email_account_service.get_owned_account(db, account_id=payload.email_account_id, user_id=current_user.id)
    except email_account_service.EmailAccountNotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e)) from e

    source = await discovery_source_repository.create(
        db, user_id=current_user.id, type_=SourceType.imap, label=f"Alertes email — {account.label}",
        config={"email_account_id": str(account.id)},
    )
    return source


@router.get("/sources", response_model=list[DiscoverySourceOut])
async def list_sources(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await discovery_source_repository.list_all(db, current_user.id)


@router.post("/run", response_model=RunDiscoveryResponse)
async def run_discovery(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> RunDiscoveryResponse:
    summary = await discovery_service.run(db, user_id=current_user.id)
    return RunDiscoveryResponse(**summary)


@router.post("/candidacies/from-posting", response_model=ApplicationOut, status_code=201)
async def create_candidacy_from_posting(
    payload: CreateCandidacyFromPostingRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> ApplicationOut:
    """Rend trackable (lettre, statut, envoi) une offre collée manuellement
    et déjà adaptée en rôle (2026-08-16, voir candidacy_service) --
    role_id doit venir d'un appel préalable à POST /onboarding/roles/from-posting."""
    try:
        app = await candidacy_service.create_from_posting(
            db, user_id=current_user.id, role_id=payload.role_id, company=payload.company,
            title=payload.title, description=payload.description, url=payload.url,
        )
    except candidacy_service.CandidacyError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e)) from e
    return _to_application_out(app, payload.url)


@router.get("/candidacies", response_model=list[ApplicationOut])
async def list_candidacies(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = await application_repository.list_for_user(db, current_user.id)
    return [_to_application_out(app, url) for app, url in rows]


@router.patch("/candidacies/{application_id}", response_model=ApplicationOut)
async def update_candidacy_status(
    application_id: uuid.UUID,
    payload: UpdateApplicationStatusRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApplicationOut:
    """Suivi manuel de statut (2026-08-15) -- le canal reste "plateforme",
    jamais d'envoi automatique ; ceci enregistre juste ce que l'utilisateur
    a fait lui-même sur le site d'origine."""
    app = await application_repository.get_owned(db, application_id=application_id, user_id=current_user.id)
    if app is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidature introuvable")
    updated = await application_repository.update_status(db, app, ApplicationStatus(payload.status))
    return _to_application_out(updated, None)


@router.post("/candidacies/{application_id}/cover-letter", response_model=ApplicationOut)
async def generate_cover_letter(
    application_id: uuid.UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> ApplicationOut:
    """Lettre de motivation adaptée à l'offre précise de cette candidature
    (2026-08-16, voir cover_letter_service) -- pas un template par rôle.
    Régénérable tant que la candidature n'est pas envoyée (écrase le
    brouillon précédent)."""
    try:
        updated = await cover_letter_service.generate(db, user_id=current_user.id, application_id=application_id)
    except cover_letter_service.CoverLetterNotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e)) from e
    except cover_letter_service.CoverLetterError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e
    return _to_application_out(updated, None)


@router.patch("/candidacies/{application_id}/cover-letter", response_model=ApplicationOut)
async def update_cover_letter(
    application_id: uuid.UUID,
    payload: UpdateCoverLetterRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApplicationOut:
    """Édition manuelle après génération (2026-08-16) -- la lettre générée par
    l'IA est un premier jet, pas un texte figé ; l'utilisateur la corrige
    ici avant l'envoi. Même garde-fou que la génération : refuse une fois
    la candidature envoyée."""
    app = await application_repository.get_owned(db, application_id=application_id, user_id=current_user.id)
    if app is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidature introuvable")
    if app.sent_at is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Candidature déjà envoyée -- la lettre est figée, impossible de la modifier")
    updated = await application_repository.set_cover_letter(db, app, payload.cover_letter_text)
    return _to_application_out(updated, None)


@router.post("/candidacies/{application_id}/send", response_model=SendApplicationResponse)
async def send_application(
    application_id: uuid.UUID,
    payload: SendApplicationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SendApplicationResponse:
    """Envoi réel canal email (2026-08-16) -- `confirm=False` (défaut) ne
    fait qu'un aperçu, aucune connexion SMTP, rien écrit en base ; seul
    `confirm=True` envoie pour de vrai et fige la candidature. Le recruteur
    doit toujours être fourni explicitement par l'utilisateur -- jamais un
    envoi automatique vers une adresse devinée."""
    try:
        result = await application_send_service.send(
            db, user_id=current_user.id, application_id=application_id, email_account_id=payload.email_account_id,
            recruiter_email=payload.recruiter_email, recruiter_name=payload.recruiter_name, dry_run=not payload.confirm,
        )
    except application_send_service.ApplicationSendNotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e)) from e
    except application_send_service.ApplicationSendError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e

    preview = None
    if result["preview"] is not None:
        p = result["preview"]
        preview = SendApplicationPreview(sender=p["from"], to=p["to"], subject=p["subject"], text=p["text"], attachment=p["attachment"])

    application_out = _to_application_out(result["application"], None) if not result["dry_run"] else None
    return SendApplicationResponse(dry_run=result["dry_run"], preview=preview, application=application_out)
