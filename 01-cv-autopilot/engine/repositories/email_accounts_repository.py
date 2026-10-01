"""Couche : Repository.

Fait : seul fichier autorisé à lire data-<client>/email_accounts.json — la
liste des comptes Gmail à interroger pour les alertes emploi.
Ne fait jamais : parler à l'API Gmail (Adapter gmail_adapter), décider si
une offre correspond au profil (Service matching_service).
"""
from __future__ import annotations

import json

from ..config import ClientConfig


def load(client: ClientConfig) -> list[str]:
    path = client.root / "email_accounts.json"
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("accounts", [])
