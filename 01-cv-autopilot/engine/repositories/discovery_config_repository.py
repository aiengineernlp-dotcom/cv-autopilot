"""Couche : Repository.

Fait : seul fichier autorisé à lire data-<client>/discovery_watchlist.json —
la liste des entreprises à surveiller (source ATS + identifiant de board).
Volontairement une liste ciblée, pas une recherche ouverte sur tout le web —
cohérent avec le principe produit "matching qualifié, pas spray-and-pray".
Ne fait jamais : appeler une API externe (Adapters), décider si une offre
correspond au profil (Service discovery_service).
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from ..config import ClientConfig


@dataclass
class WatchlistEntry:
    provider: str  # "greenhouse" | "lever"
    board_token: str
    company_display_name: str


def load(client: ClientConfig) -> list[WatchlistEntry]:
    path = client.root / "discovery_watchlist.json"
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [WatchlistEntry(**e) for e in data.get("sources", [])]
