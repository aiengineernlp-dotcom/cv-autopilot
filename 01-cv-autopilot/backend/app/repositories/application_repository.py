"""Couche : Repository -- seul fichier autorisé à faire une requête SQL sur
`applications` (remplace tracker-candidatures.md + le dossier queue/ de la
Phase 1, voir docs/DATA_MODEL.md)."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Application, Posting
from ..models.enums import ApplicationStatus, ChannelType


async def create_queued(
    db: AsyncSession, *, user_id: uuid.UUID, posting_id: uuid.UUID, role_id: uuid.UUID,
    company: str, title: str, match_score: int | None, notes: str,
) -> Application:
    """match_score=None pour une candidature créée manuellement (voir
    candidacy_service.create_from_posting) -- l'utilisateur a déjà choisi ce
    rôle pour cette offre précise, aucun score de matching à calculer."""
    app = Application(
        user_id=user_id, posting_id=posting_id, role_id=role_id, company=company, title=title,
        channel=ChannelType.platform, status=ApplicationStatus.queued, match_score=match_score, notes=notes,
    )
    db.add(app)
    await db.commit()
    await db.refresh(app)
    return app


async def list_for_user(db: AsyncSession, user_id: uuid.UUID) -> list[tuple[Application, str | None]]:
    """Renvoie (Application, url_de_l'offre) -- l'URL vit sur `postings`, pas
    sur `applications` (voir docs/DATA_MODEL.md) mais le Router en a besoin
    pour afficher le lien "postuler toi-même sur le lien d'origine" (2026-08-15,
    manquait -- une candidature "queued" sans lien cliquable est inutilisable)."""
    result = await db.execute(
        select(Application, Posting.url)
        .outerjoin(Posting, Posting.id == Application.posting_id)
        .where(Application.user_id == user_id)
        .order_by(Application.created_at.desc())
    )
    return [(app, url) for app, url in result.all()]


async def get_owned(db: AsyncSession, *, application_id: uuid.UUID, user_id: uuid.UUID) -> Application | None:
    result = await db.execute(
        select(Application).where(Application.id == application_id, Application.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def update_status(db: AsyncSession, application: Application, status: ApplicationStatus) -> Application:
    """Suivi de statut manuel (2026-08-15) -- aucune règle d'enchaînement
    imposée (l'utilisateur peut passer directement à "rejected" s'il a
    postulé et n'a jamais eu de réponse, par exemple) ; seule règle : une
    fois `sent_at` posé, il n'est jamais réécrit -- même principe que
    `cover_letter_text` figée au moment de l'envoi."""
    application.status = status
    if status == ApplicationStatus.sent and application.sent_at is None:
        application.sent_at = dt.datetime.now(dt.timezone.utc)
    await db.commit()
    await db.refresh(application)
    return application


async def mark_sent(
    db: AsyncSession, application: Application, *,
    cv_file_id: uuid.UUID, recruiter_email: str, recruiter_name: str | None,
) -> Application:
    """Envoi réel canal email (2026-08-16, voir application_send_service) --
    fige tout ce qui a servi à l'envoi en une seule transaction (pas
    `update_status` + un update séparé, pour ne jamais laisser un état
    intermédiaire où `sent_at` est posé sans que `cv_file_id`/`recruiter_email`
    le soient déjà). Relance à J+7, même délai que la Phase 1 CLI
    (`followup_service`)."""
    application.channel = ChannelType.email
    application.status = ApplicationStatus.sent
    application.cv_file_id = cv_file_id
    application.recruiter_email = recruiter_email
    application.recruiter_name = recruiter_name
    application.sent_at = dt.datetime.now(dt.timezone.utc)
    application.follow_up_due_at = application.sent_at + dt.timedelta(days=7)
    await db.commit()
    await db.refresh(application)
    return application


async def set_cover_letter(db: AsyncSession, application: Application, cover_letter_text: str) -> Application:
    """Écrase le brouillon précédent -- seul `sent_at` posé fige le texte pour
    de bon (voir cover_letter_service.generate, qui refuse de rappeler ceci
    une fois l'envoi effectué)."""
    application.cover_letter_text = cover_letter_text
    await db.commit()
    await db.refresh(application)
    return application


async def exists_for_posting(db: AsyncSession, user_id: uuid.UUID, posting_id: uuid.UUID) -> bool:
    result = await db.execute(
        select(Application.id).where(Application.user_id == user_id, Application.posting_id == posting_id)
    )
    return result.scalar_one_or_none() is not None
