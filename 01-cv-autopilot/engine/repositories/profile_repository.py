"""Couche : Repository.

Fait : seul fichier autorisé à lire data-<client>/profile.json.
Ne fait jamais : décider quelle adresse utiliser pour l'envoi
(Service application_service), envoyer un email (Adapter resend_adapter).
"""
from __future__ import annotations

import json

from ..config import ClientConfig


def load_profile(client: ClientConfig) -> dict:
    path = client.root / "profile.json"
    return json.loads(path.read_text(encoding="utf-8"))
