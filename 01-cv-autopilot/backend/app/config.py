"""Couche : config — chargée une fois au démarrage, injectée partout via Settings.

Fait : lit les variables d'environnement (.env), les valide, les expose comme
un objet Python typé.
Ne fait jamais : contenir une valeur secrète en dur (tout vient de l'environnement).
"""
from __future__ import annotations

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://localhost/cv_autopilot_dev"

    @field_validator("database_url")
    @classmethod
    def _use_asyncpg_driver(cls, v: str) -> str:
        # Railway (et la plupart des hébergeurs) fournissent DATABASE_URL en
        # "postgresql://" ou "postgres://" -- l'app a besoin du driver
        # asyncpg explicite. Normalisé ici plutôt que de compter sur
        # chaque environnement pour éditer la variable à la main.
        if v.startswith("postgres://"):
            return "postgresql+asyncpg://" + v[len("postgres://"):]
        if v.startswith("postgresql://"):
            return "postgresql+asyncpg://" + v[len("postgresql://"):]
        return v

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    openrouter_api_key: str | None = None
    openrouter_model: str = "anthropic/claude-sonnet-4.5"

    cors_allow_origins: list[str] = ["http://localhost:3000"]

    # Bêta privée (décision du 2026-08-14) -- /auth/signup exige une invitation
    # (table beta_invites) tant que True. Passer à False pour l'ouverture
    # publique -- aucun changement de code requis.
    beta_invite_only: bool = True

    # Protège /admin/* (gestion des invitations) -- secret partagé simple,
    # pas un système de rôles complet : un seul opérateur (l'utilisateur) à
    # ce stade, pas besoin de plus.
    admin_token: str | None = None

    # Chiffre les secrets par utilisateur (mots de passe IMAP, tokens Gmail)
    # avant écriture en base -- voir app/core/crypto.py et docs/DATA_MODEL.md
    secret_encryption_key: str | None = None


settings = Settings()
