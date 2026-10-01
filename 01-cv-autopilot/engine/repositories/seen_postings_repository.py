"""Couche : Repository.

Fait : seul fichier autorisé à lire/écrire data-<client>/seen_postings.json —
la liste des offres déjà traitées (source + id externe), pour ne jamais
retraiter ou re-candidater deux fois sur la même offre.
Ne fait jamais : décider si une offre doit être traitée (Service
discovery_service).
"""
from __future__ import annotations

import json
from pathlib import Path

from ..config import ClientConfig


def _path(client: ClientConfig) -> Path:
    return client.root / "seen_postings.json"


def load_seen(client: ClientConfig) -> set[str]:
    path = _path(client)
    if not path.is_file():
        return set()
    return set(json.loads(path.read_text(encoding="utf-8")))


def mark_seen(client: ClientConfig, keys: list[str]) -> None:
    if not keys:
        return
    path = _path(client)
    seen = load_seen(client)
    seen.update(keys)
    path.write_text(json.dumps(sorted(seen), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
