"""Couche : Repository.

Fait : seul fichier autorisé à lire data-<client>/imap_accounts.json — la
liste des boîtes mail IMAP à interroger (host/port/utilisateur — pas de
secret ici, le mot de passe reste dans .env).
Ne fait jamais : parler au serveur IMAP (Adapter imap_adapter), lire les
mots de passe eux-mêmes (ça reste dans .env, chargé par cli.py via
python-dotenv, jamais par ce Repository).
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from ..config import ClientConfig


@dataclass
class ImapAccount:
    label: str
    host: str
    port: int
    username: str


def load(client: ClientConfig) -> list[ImapAccount]:
    path = client.root / "imap_accounts.json"
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [ImapAccount(**a) for a in data.get("accounts", [])]
