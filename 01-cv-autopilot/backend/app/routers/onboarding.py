"""Couche : Router (UI HTTP) -- onboarding. Parse la requête, appelle
onboarding_service, sérialise. Ne fait jamais : logique métier, requête SQL,
appel LLM -- tout passe par le Service."""
from __future__ import annotations

import uuid
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from ..core import storage
from ..core.deps import get_current_user
from ..core.llm import LlmNotConfiguredError, LlmResponseError
from ..db import get_db
from ..models import User
from ..repositories import cv_file_repository, cv_upload_repository, draft_repository, role_repository
from ..schemas.onboarding import (
    CvFileOut,
    CvUploadOut,
    DraftOut,
    ReviewDraftRequest,
    RoleFromPostingRequest,
    RoleOut,
    RoleTargetRequest,
)
from ..services import cv_generation_service, onboarding_service

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


def _handle_onboarding_errors(e: Exception):
    # Sous-classes de OnboardingError vérifiées AVANT le cas générique --
    # sinon `isinstance(e, OnboardingError)` les intercepte toutes en premier
    # et leur donne 409 au lieu du code plus précis voulu ci-dessous.
    if isinstance(e, onboarding_service.CvUploadNotFoundError):
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e)) from e
    if isinstance(e, onboarding_service.RoleNotFoundError):
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e)) from e
    if isinstance(e, onboarding_service.OnboardingError):
        raise HTTPException(status.HTTP_409_CONFLICT, str(e)) from e
    if isinstance(e, LlmNotConfiguredError):
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(e)) from e
    if isinstance(e, LlmResponseError):
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(e)) from e
    if isinstance(e, cv_generation_service.CvGenerationError):
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e)) from e
    raise e


@router.post("/cv-uploads", response_model=CvUploadOut, status_code=status.HTTP_201_CREATED)
async def upload_cv(
    file: UploadFile, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> CvUploadOut:
    content = await file.read()
    try:
        upload = await onboarding_service.upload_cv(
            db, user_id=current_user.id, file_name=file.filename or "cv", mime_type=file.content_type or "", content=content,
        )
    except (onboarding_service.OnboardingError, LlmNotConfiguredError, LlmResponseError) as e:
        _handle_onboarding_errors(e)
    return upload


@router.get("/cv-uploads", response_model=list[CvUploadOut])
async def list_cv_uploads(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await cv_upload_repository.list_uploads(db, current_user.id)


@router.delete("/cv-uploads/{upload_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cv_upload(
    upload_id: uuid.UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> None:
    try:
        await onboarding_service.delete_cv_upload(db, user_id=current_user.id, upload_id=upload_id)
    except onboarding_service.OnboardingError as e:
        _handle_onboarding_errors(e)


@router.delete("/profile", status_code=status.HTTP_204_NO_CONTENT)
async def reset_profile(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> None:
    """Réinitialise CV uploadés + draft pour repartir de zéro. Ne touche
    jamais aux rôles déjà créés (voir onboarding_service.reset_profile)."""
    await onboarding_service.reset_profile(db, user_id=current_user.id)


@router.post("/merge", response_model=DraftOut)
async def merge_uploads(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> DraftOut:
    try:
        return await onboarding_service.merge_uploads(db, user_id=current_user.id)
    except (onboarding_service.OnboardingError, LlmNotConfiguredError, LlmResponseError) as e:
        _handle_onboarding_errors(e)


@router.get("/draft", response_model=DraftOut)
async def get_draft(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> DraftOut:
    draft = await draft_repository.get_active_draft(db, current_user.id) or await draft_repository.get_confirmed_draft(db, current_user.id)
    if draft is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aucun draft -- upload un CV puis lance la fusion")
    return draft


@router.patch("/draft", response_model=DraftOut)
async def review_draft(
    payload: ReviewDraftRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> DraftOut:
    try:
        return await onboarding_service.review_draft(db, user_id=current_user.id, reviewed_extraction=payload.reviewed_extraction)
    except onboarding_service.OnboardingError as e:
        _handle_onboarding_errors(e)


@router.post("/draft/confirm", response_model=DraftOut)
async def confirm_draft(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> DraftOut:
    try:
        return await onboarding_service.confirm_draft(db, user_id=current_user.id)
    except onboarding_service.OnboardingError as e:
        _handle_onboarding_errors(e)


@router.post("/roles", response_model=RoleOut, status_code=status.HTTP_201_CREATED)
async def create_role(
    payload: RoleTargetRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> RoleOut:
    try:
        role, coverage_notes = await onboarding_service.create_role(db, user_id=current_user.id, name=payload.name)
    except (onboarding_service.OnboardingError, LlmNotConfiguredError, LlmResponseError) as e:
        _handle_onboarding_errors(e)
    return RoleOut.model_validate(role).model_copy(update={"coverage_notes": coverage_notes})


@router.post("/roles/from-posting", response_model=RoleOut, status_code=status.HTTP_201_CREATED)
async def create_role_from_posting(
    payload: RoleFromPostingRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> RoleOut:
    """Adaptation par offre précise (2026-08-15) -- voir onboarding_service.create_role_from_posting."""
    try:
        role, coverage_notes = await onboarding_service.create_role_from_posting(
            db, user_id=current_user.id, title=payload.title, company=payload.company, description=payload.description,
        )
    except (onboarding_service.OnboardingError, LlmNotConfiguredError, LlmResponseError) as e:
        _handle_onboarding_errors(e)
    return RoleOut.model_validate(role).model_copy(update={"coverage_notes": coverage_notes})


@router.get("/roles", response_model=list[RoleOut])
async def list_roles(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await role_repository.list_roles(db, current_user.id)


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: uuid.UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> None:
    try:
        await onboarding_service.delete_role(db, user_id=current_user.id, role_id=role_id)
    except onboarding_service.OnboardingError as e:
        _handle_onboarding_errors(e)


@router.post("/roles/{role_id}/generate-cv", response_model=CvFileOut, status_code=status.HTTP_201_CREATED)
async def generate_cv(
    role_id: uuid.UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> CvFileOut:
    try:
        _, version = await cv_generation_service.generate(db, user_id=current_user.id, role_id=role_id)
    except cv_generation_service.CvGenerationError as e:
        _handle_onboarding_errors(e)
    return CvFileOut(version=version, download_url=f"/onboarding/roles/{role_id}/cv")


@router.get("/roles/{role_id}/cv")
async def download_cv(
    role_id: uuid.UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> Response:
    role = await role_repository.get_role(db, role_id=role_id, user_id=current_user.id)
    if role is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rôle introuvable")

    cv_file = await cv_file_repository.get_latest(db, role_id)
    if cv_file is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aucun CV généré pour ce rôle -- POST .../generate-cv d'abord")

    content = storage.read_generated_file(cv_file.storage_key)
    file_name = f"CV_{role.name.replace(' ', '_')}.docx"
    # Content-Disposition doit rester encodable en Latin-1 -- un nom de rôle
    # avec un caractère hors ASCII (tiret cadratin d'une adaptation par
    # offre précise, accents, etc.) faisait planter la réponse entière en
    # 500 (UnicodeEncodeError, trouvé en réel le 2026-08-15, jamais vu avant
    # car les noms de rôle générique testés jusqu'ici étaient tous ASCII).
    # Secours ASCII pour les vieux clients + filename* UTF-8 (RFC 6266) pour
    # un nom correct partout ailleurs.
    ascii_fallback = file_name.encode("ascii", errors="replace").decode("ascii")
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{quote(file_name)}"
        },
    )
