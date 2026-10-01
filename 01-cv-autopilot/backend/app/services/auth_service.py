"""Couche : Service -- logique métier de l'inscription/connexion. Orchestre
Repository (user_repository, beta_invite_repository) + core.security, jamais
de requête SQL directe ici (délègue toujours au Repository).

Bêta privée (décision produit du 2026-08-14, mécanisme construit le
2026-08-15) : `settings.beta_invite_only` -- à `True` par défaut, `/auth/signup`
refuse toute adresse absente de `beta_invites`. Passer à l'ouverture
publique ("prêt pour le public à tout moment") ne demande de changer ni le
code ni le schéma -- juste `BETA_INVITE_ONLY=false` côté variables
d'environnement."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..core.security import create_access_token, hash_password, verify_password
from ..models import User
from ..repositories import beta_invite_repository, user_repository


class AuthError(RuntimeError):
    """Erreur métier (email déjà pris, identifiants invalides) -- jamais une erreur technique brute."""


class NotInvitedError(AuthError):
    """Distincte de AuthError générique pour que le Router la mappe en 403
    (accès refusé) plutôt qu'en 409 (conflit) -- sémantique HTTP différente,
    pas la même situation qu'un email déjà pris."""


async def signup(db: AsyncSession, *, email: str, password: str, full_name: str) -> User:
    if settings.beta_invite_only and not await beta_invite_repository.is_invited(db, email):
        raise NotInvitedError("Cette bêta est sur invitation pour l'instant -- demande une invitation.")

    if await user_repository.get_by_email(db, email) is not None:
        raise AuthError("Un compte existe déjà avec cet email")

    return await user_repository.create(db, email=email, password_hash=hash_password(password), full_name=full_name)


async def login(db: AsyncSession, *, email: str, password: str) -> str:
    user = await user_repository.get_by_email(db, email)
    if user is None or user.password_hash is None or not verify_password(password, user.password_hash):
        raise AuthError("Email ou mot de passe incorrect")

    return create_access_token(user.id)
