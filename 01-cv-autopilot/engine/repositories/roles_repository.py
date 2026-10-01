"""Couche : Repository.

Fait : seul fichier autorisé à lire/écrire data-<client>/roles.json — charge la liste
des rôles, retrouve un rôle par id, marque un rôle comme "CV généré".
Ne fait jamais : scorer un rôle ou décider lequel correspond à une offre
(Service matching_service), construire un CV (Presentation cv_style).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ..config import ClientConfig


@dataclass
class Role:
    id: str
    name: str
    keywords: list
    cv_path: str | None
    cover_letter_number: int
    status: str
    notes: str = ""


def _path(client: ClientConfig) -> Path:
    return client.root / "roles.json"


def load_roles(client: ClientConfig) -> list[Role]:
    data = json.loads(_path(client).read_text(encoding="utf-8"))
    return [Role(**r) for r in data["roles"]]


def find_by_id(client: ClientConfig, role_id: str) -> Role | None:
    return next((r for r in load_roles(client) if r.id == role_id), None)


def mark_cv_generated(client: ClientConfig, role_id: str, cv_path: str, notes: str = "") -> None:
    path = _path(client)
    data = json.loads(path.read_text(encoding="utf-8"))
    for r in data["roles"]:
        if r["id"] == role_id:
            r["cv_path"] = cv_path
            r["status"] = "cv_disponible"
            r["notes"] = notes
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
