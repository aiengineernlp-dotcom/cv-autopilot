"""Couche : Service -- opérations d'administration de la bêta privée.
Ne fait jamais : requête SQL directe (délègue toujours au Repository
concerné), servir une route HTTP (ça reste dans le Router)."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from ..core import storage
from ..repositories import beta_invite_repository, user_repository


class AdminError(RuntimeError):
    """Erreur métier admin (compte introuvable...) -- jamais une exception technique brute."""


class UserNotFoundError(AdminError):
    """Distincte pour que le Router la mappe en 404."""


async def delete_user(db: AsyncSession, *, email: str) -> None:
    """Supprime un compte de test et tout ce qui lui appartient -- ajouté
    le 2026-08-15 pour nettoyer les comptes créés pendant les tests en
    production (pas de clé SSH pour le faire directement en base). CASCADE
    côté schéma efface déjà profiles/cv_uploads/experiences/drafts/roles/
    discovery_sources/postings/applications ; les fichiers physiques et
    l'invitation bêta (pas liée par FK) doivent être effacés à part."""
    user = await user_repository.get_by_email(db, email)
    if user is None:
        raise UserNotFoundError("Utilisateur introuvable")

    storage.delete_user_storage(user.id)
    await user_repository.delete(db, user)
    await beta_invite_repository.delete_by_email(db, email)
