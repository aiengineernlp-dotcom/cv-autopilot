"""Couche : Repository -- seul fichier autorisé à faire une requête SQL sur
`users`/`profiles`. Ne fait jamais : hacher un mot de passe, décider d'une
règle métier (ça reste dans le Service appelant)."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Profile, User


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def list_all(db: AsyncSession) -> list[User]:
    """Utilisé par l'administration (2026-08-15) pour retrouver les comptes
    créés avant l'activation du filtre d'invitation -- absents de
    `beta_invites`, donc invisibles depuis GET /admin/beta-invites seul."""
    result = await db.execute(select(User).order_by(User.created_at))
    return list(result.scalars().all())


async def get_profile(db: AsyncSession, user_id: uuid.UUID) -> Profile | None:
    result = await db.execute(select(Profile).where(Profile.user_id == user_id))
    return result.scalar_one_or_none()


async def update_profile_from_draft(db: AsyncSession, user_id: uuid.UUID, extraction: dict) -> Profile:
    """Applique les champs profil d'un draft confirmé (headline, contact,
    education, certifications) -- appelé une seule fois, à la confirmation."""
    profile = await get_profile(db, user_id)
    contact = extraction.get("contact", {})

    profile.headline = extraction.get("headline") or profile.headline
    profile.phone = contact.get("phone") or profile.phone
    profile.location = contact.get("location") or profile.location
    profile.linkedin_url = contact.get("linkedin_url") or profile.linkedin_url
    profile.github_url = contact.get("github_url") or profile.github_url
    profile.education = extraction.get("education", profile.education)
    profile.certifications = extraction.get("certifications", profile.certifications)

    await db.commit()
    await db.refresh(profile)
    return profile


async def delete(db: AsyncSession, user: User) -> None:
    """Utilisé par l'administration de la bêta (2026-08-15) pour retirer un
    compte de test -- CASCADE côté schéma supprime déjà profiles/cv_uploads/
    experiences/drafts/roles/discovery_sources/postings/applications liés.
    Le Service appelant doit avoir déjà effacé les fichiers physiques de cet
    utilisateur avant d'appeler ceci (voir admin_service.delete_user)."""
    await db.delete(user)
    await db.commit()


async def create(db: AsyncSession, *, email: str, password_hash: str, full_name: str) -> User:
    user = User(email=email, password_hash=password_hash, full_name=full_name)
    db.add(user)
    await db.flush()  # obtenir user.id avant de créer le profil qui en dépend

    profile = Profile(user_id=user.id)
    db.add(profile)

    await db.commit()
    await db.refresh(user)
    return user
