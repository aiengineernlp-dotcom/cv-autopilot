"""Couche : infrastructure sécurité -- chiffrement applicatif des secrets par
utilisateur (mots de passe IMAP, tokens Gmail). Décision tranchée le
2026-08-15 (voir docs/DATA_MODEL.md, "Ouvert, pas encore tranché") : une clé
unique côté serveur (jamais en DB) chiffre chaque secret avant écriture --
`discovery_sources.credential_ref` stocke le texte chiffré, jamais le secret
en clair. Suffisant pour une bêta privée ; un secrets manager dédié
(Infisical, Doppler...) reste une amélioration valable avant une ouverture
publique large, pas un prérequis aujourd'hui.

Fernet (AEAD symétrique, `cryptography`) : authentifié, empêche la
falsification silencieuse, pas seulement la lecture.
Ne fait jamais : décider quand chiffrer/déchiffrer -- ça reste au Service
appelant (discovery_service, pas encore construit)."""
from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from ..config import settings


class CryptoNotConfiguredError(RuntimeError):
    """SECRET_ENCRYPTION_KEY manquant -- erreur métier explicite, pas un crash."""


def _fernet() -> Fernet:
    if not settings.secret_encryption_key:
        raise CryptoNotConfiguredError("SECRET_ENCRYPTION_KEY manquant dans .env")
    return Fernet(settings.secret_encryption_key.encode("utf-8"))


def encrypt_secret(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_secret(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken as e:
        raise CryptoNotConfiguredError("Secret illisible -- clé de chiffrement changée ou donnée corrompue") from e
