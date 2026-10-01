"""Couche : Config.

Fait : résout le dossier racine d'un client (data-<nom>/) dans l'arborescence du produit.
Ne fait jamais : lire le contenu d'un fichier, connaître le format d'un fichier précis
(roles.json, tracker.md, profile.json...) — c'est le rôle de chaque Repository.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

PRODUCT_ROOT = Path(__file__).resolve().parent.parent  # .../01-cv-autopilot


@dataclass
class ClientConfig:
    client_id: str
    root: Path


def load_client(client_id: str) -> ClientConfig:
    root = PRODUCT_ROOT / client_id
    if not root.is_dir():
        raise FileNotFoundError(f"Dossier client introuvable : {root}")
    return ClientConfig(client_id=client_id, root=root)
