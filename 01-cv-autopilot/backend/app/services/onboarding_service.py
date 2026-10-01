"""Couche : Service -- orchestrateur de l'onboarding. Enchaîne les 4 briques
(extraction, fusion, adaptation, mots-clés -- chacune déjà validée en
prototype, voir prototypes/*/output/RESULTS.md) avec les Repositories.
C'est le seul fichier autorisé à faire parler plusieurs Repositories entre
eux pour ce domaine.
Ne fait jamais : requête SQL directe (délègue toujours au Repository
concerné), appeler le LLM directement (délègue aux 4 Services de brique)."""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import CvUpload, ExtractedProfileDraft, Role
from ..repositories import cv_file_repository, cv_upload_repository, draft_repository, role_repository, user_repository
from ..models.enums import CvUploadStatus
from . import cv_extraction_service, cv_merge_service, matching_keywords_service, role_adaptation_service
from ..core import storage

MAX_CV_UPLOADS = 3  # décision produit du 2026-08-15 -- voir docs/DATA_MODEL.md


class OnboardingError(RuntimeError):
    """Erreur métier (plafond d'upload atteint, draft non confirmé...) -- jamais une exception technique brute."""


class CvUploadNotFoundError(OnboardingError):
    """Distincte de OnboardingError générique pour que le Router la mappe en
    404, pas 409 -- pas un conflit, une ressource absente ou pas à toi."""


class RoleNotFoundError(OnboardingError):
    """Même raisonnement que CvUploadNotFoundError -- 404, pas 409."""


async def upload_cv(db: AsyncSession, *, user_id: uuid.UUID, file_name: str, mime_type: str, content: bytes) -> CvUpload:
    current_count = await cv_upload_repository.count_uploads(db, user_id)
    if current_count >= MAX_CV_UPLOADS:
        raise OnboardingError(f"Plafond de {MAX_CV_UPLOADS} CV atteint pour cet utilisateur")

    storage_key = storage.save_upload(user_id, file_name, content)
    upload = await cv_upload_repository.create_upload(
        db, user_id=user_id, file_name=file_name, storage_key=storage_key,
        mime_type=mime_type, size_bytes=len(content),
    )

    await cv_upload_repository.set_status(db, upload, CvUploadStatus.extracting)
    cv_text = storage.extract_text(storage_key, mime_type)
    raw_extraction = cv_extraction_service.extract(cv_text)

    await cv_upload_repository.save_extraction(db, cv_upload_id=upload.id, raw_extraction=raw_extraction)
    await cv_upload_repository.set_status(db, upload, CvUploadStatus.extracted)
    return upload


async def delete_cv_upload(db: AsyncSession, *, user_id: uuid.UUID, upload_id: uuid.UUID) -> None:
    """Retire un CV de la liste -- libère une place sous le plafond (voir
    demande utilisateur du 2026-08-15 : pouvoir enlever un CV plutôt que
    rester bloqué à 3 pour toujours). N'affecte jamais un profil déjà
    confirmé -- confirm_draft a déjà copié ce dont il avait besoin dans
    `experiences`/`profiles`, indépendant de l'upload source."""
    upload = await cv_upload_repository.get_owned_upload(db, upload_id=upload_id, user_id=user_id)
    if upload is None:
        raise CvUploadNotFoundError("CV introuvable")

    storage.delete_upload(upload.storage_key)
    await cv_upload_repository.delete(db, upload)


async def merge_uploads(db: AsyncSession, *, user_id: uuid.UUID) -> ExtractedProfileDraft:
    uploads = [u for u in await cv_upload_repository.list_uploads(db, user_id) if u.status == CvUploadStatus.extracted]
    if not uploads:
        raise OnboardingError("Aucun CV extrait à fusionner -- upload d'abord au moins un CV")

    extractions = await cv_upload_repository.list_extractions_for_uploads(db, [u.id for u in uploads])
    raw_by_extractions = [e.raw_extraction for e in extractions]

    if len(raw_by_extractions) == 1:
        # Rien à fusionner -- éviter un appel LLM inutile pour un cas trivial
        merged = {**raw_by_extractions[0], "merge_notes": ["Un seul CV uploadé -- pas de fusion nécessaire."], "conflicts": []}
    else:
        merged = cv_merge_service.merge(raw_by_extractions, [u.file_name for u in uploads])

    return await draft_repository.upsert_draft(
        db, user_id=user_id, raw_extraction=merged, conflicts=merged.get("conflicts", []),
        source_upload_ids=[u.id for u in uploads],
    )


async def review_draft(db: AsyncSession, *, user_id: uuid.UUID, reviewed_extraction: dict) -> ExtractedProfileDraft:
    draft = await draft_repository.get_active_draft(db, user_id)
    if draft is None:
        raise OnboardingError("Aucun draft en attente de relecture -- lance d'abord la fusion")
    return await draft_repository.update_review(db, draft, reviewed_extraction)


async def confirm_draft(db: AsyncSession, *, user_id: uuid.UUID) -> ExtractedProfileDraft:
    draft = await draft_repository.get_active_draft(db, user_id)
    if draft is None:
        raise OnboardingError("Aucun draft en attente de relecture -- lance d'abord la fusion")

    if draft.conflicts and draft.reviewed_extraction is None:
        raise OnboardingError(
            "Des désaccords entre tes CV doivent être tranchés avant de confirmer -- "
            "soumets une relecture (reviewed_extraction) qui les résout."
        )

    final = draft.reviewed_extraction or draft.raw_extraction
    await role_repository.sync_experiences(db, user_id, final.get("experiences", []))
    await user_repository.update_profile_from_draft(db, user_id, final)
    return await draft_repository.confirm(db, draft)


async def _adapt_and_persist_role(
    db: AsyncSession, *, user_id: uuid.UUID, display_name: str, target_role_text: str,
) -> tuple[Role, list[str]]:
    """Partagé par create_role (nom de rôle générique) et
    create_role_from_posting (texte complet d'une offre précise, 2026-08-15)
    -- role_adaptation_service.adapt() ne fait aucune différence entre les
    deux, "target_role" est juste le texte contre lequel adapter le profil,
    qu'il s'agisse d'un nom court ("Data Analyst") ou d'une offre entière
    collée par l'utilisateur. Zéro changement de prompt nécessaire."""
    draft = await draft_repository.get_confirmed_draft(db, user_id)
    if draft is None:
        raise OnboardingError("Le profil doit être relu et confirmé avant de générer un rôle")

    base_profile = draft.reviewed_extraction or draft.raw_extraction
    adapted = role_adaptation_service.adapt(base_profile, target_role_text)
    keywords_result = matching_keywords_service.generate(adapted)

    # roles a une contrainte UNIQUE(user_id, name) -- sans ce contrôle,
    # coller deux fois la même offre (même titre + même entreprise) ou
    # créer deux rôles du même nom plantait en 500 brut (trouvé en réel,
    # 2026-08-15) au lieu d'un comportement géré. Désambiguïse plutôt que
    # de bloquer -- l'utilisateur ne perd jamais son adaptation pour ça.
    unique_name = display_name
    suffix = 2
    while await role_repository.name_exists(db, user_id=user_id, name=unique_name):
        unique_name = f"{display_name} ({suffix})"
        suffix += 1

    role = await role_repository.create_role(
        db, user_id=user_id, name=unique_name, summary=adapted.get("summary"),
        skills=adapted.get("skills", []), keywords=keywords_result.get("keywords", []),
    )

    experiences_by_title = {e.position_title: e for e in await role_repository.list_experiences(db, user_id)}
    for i, exp in enumerate(adapted.get("experiences", [])):
        match = experiences_by_title.get(exp.get("position_title"))
        if match is not None:
            await role_repository.add_experience_bullets(
                db, role_id=role.id, experience_id=match.id, bullets=exp.get("tailored_bullets", []), sort_order=i,
            )

    for i, project in enumerate(adapted.get("key_projects", [])):
        await role_repository.add_role_project(
            db, role_id=role.id, title=project.get("title", ""), subtitle=project.get("subtitle"),
            year=project.get("year"), bullets=project.get("bullets", []), sort_order=i,
        )

    return role, adapted.get("coverage_notes", [])


async def create_role(db: AsyncSession, *, user_id: uuid.UUID, name: str) -> tuple[Role, list[str]]:
    return await _adapt_and_persist_role(db, user_id=user_id, display_name=name, target_role_text=name)


async def create_role_from_posting(
    db: AsyncSession, *, user_id: uuid.UUID, title: str, company: str | None, description: str,
) -> tuple[Role, list[str]]:
    """Adaptation par OFFRE PRÉCISE, pas par catégorie de rôle (2026-08-15,
    décision produit après que l'utilisateur ait remarqué que l'adaptation
    par nom de rôle générique n'était pas ce qui avait été promis). Marche
    pour n'importe quel métier -- l'utilisateur colle le texte d'une offre
    trouvée n'importe où (LinkedIn, un ami, une affiche), pas seulement les
    entreprises de la liste de découverte automatique."""
    target_role_text = (
        f"{title} chez {company}\n\nDescription du poste :\n{description}"
        if company
        else f"{title}\n\nDescription du poste :\n{description}"
    )
    display_name = f"{title} — {company}" if company else title
    return await _adapt_and_persist_role(db, user_id=user_id, display_name=display_name, target_role_text=target_role_text)


async def reset_profile(db: AsyncSession, *, user_id: uuid.UUID) -> None:
    """Réinitialisation demandée par l'utilisateur le 2026-08-15 (après avoir
    remarqué que supprimer tous ses CV ne vidait pas l'écran de relecture) :
    efface les CV uploadés et le draft (actif ou confirmé), pour repartir de
    zéro à l'étape 1.

    Ne touche JAMAIS aux rôles déjà créés, volontairement -- un rôle a son
    propre CV généré, potentiellement déjà téléchargé et envoyé à un vrai
    employeur, et c'est aujourd'hui la seule trace qu'une candidature créée
    depuis l'onboarding (par opposition à la découverte automatique, qui
    logue dans `applications`) ait existé. Réinitialiser le profil de base
    ne doit jamais effacer un travail déjà utilisé ailleurs -- même principe
    que "cover_letter_text figée au moment de l'envoi" pour les candidatures."""
    uploads = await cv_upload_repository.list_uploads(db, user_id)
    for upload in uploads:
        storage.delete_upload(upload.storage_key)

    await cv_upload_repository.delete_all_for_user(db, user_id)
    await draft_repository.delete_all_for_user(db, user_id)


async def delete_role(db: AsyncSession, *, user_id: uuid.UUID, role_id: uuid.UUID) -> None:
    """Suppression explicite et ciblée d'UN rôle, demandée par l'utilisateur
    le 2026-08-15 comme alternative sûre à un reset qui toucherait aussi les
    rôles. Contrairement à reset_profile, celle-ci EST destructive pour le
    rôle visé -- c'est le but, un geste volontaire sur un élément précis,
    pas un effet de bord d'une autre action."""
    role = await role_repository.get_role(db, role_id=role_id, user_id=user_id)
    if role is None:
        raise RoleNotFoundError("Rôle introuvable")

    for cv_file in await cv_file_repository.list_for_role(db, role_id):
        storage.delete_generated_file(cv_file.storage_key)

    await role_repository.delete_role(db, role)
