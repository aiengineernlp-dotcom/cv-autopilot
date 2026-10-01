"""Couche : Repository.

Fait : seul fichier autorisé à lire data-<client>/cv_content.json — le texte réel
des CV (résumé, expérience, projets, compétences) par rôle, propre à un client.
C'est ce qui rend le moteur vendable : un nouveau client a son propre
cv_content.json, jamais mélangé à celui d'un autre.
Ne fait jamais : construire le document Word (Presentation cv_style), décider
où sauvegarder le fichier généré (Service cv_generation_service).
"""
from __future__ import annotations

import json

from ..config import ClientConfig


def load(client: ClientConfig) -> dict:
    path = client.root / "cv_content.json"
    return json.loads(path.read_text(encoding="utf-8"))
