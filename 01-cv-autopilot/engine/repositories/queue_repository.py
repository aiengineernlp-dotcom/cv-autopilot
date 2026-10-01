"""Couche : Repository.

Fait : seul fichier autorisé à écrire dans data-<client>/queue/ — dépose sujet, corps
et CV d'une candidature "plateforme" en attente de validation humaine.
Ne fait jamais : décider si une candidature doit être mise en file plutôt
qu'envoyée par email (Service application_service).
"""
from __future__ import annotations

import shutil
from pathlib import Path

from ..config import ClientConfig


def enqueue(client: ClientConfig, folder_name: str, subject: str, body: str, cv_path: Path | None) -> Path:
    base = client.root / "queue" / folder_name
    dest = base
    n = 2
    while dest.exists():  # jamais d'écrasement silencieux d'une préparation existante
        dest = client.root / "queue" / f"{folder_name}-{n}"
        n += 1
    dest.mkdir(parents=True)
    (dest / "subject.txt").write_text(subject, encoding="utf-8")
    (dest / "body.txt").write_text(body, encoding="utf-8")
    if cv_path is not None and cv_path.is_file():
        shutil.copy(cv_path, dest / cv_path.name)
    return dest
