"""Couche : Adapter. Copie de ../engine/adapters/lever_adapter.py -- API
publique (api.lever.co), même raisonnement que greenhouse_adapter.py.
Ne fait jamais : décider si une offre correspond au profil, écrire en base.
"""
from __future__ import annotations

import requests

from .posting import Posting

ENDPOINT = "https://api.lever.co/v0/postings/{token}"


def fetch(board_token: str, company_display_name: str) -> list[Posting]:
    resp = requests.get(ENDPOINT.format(token=board_token), params={"mode": "json"}, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict):
        return []  # board introuvable -- Lever répond {"ok": false, ...} dans ce cas

    return [
        Posting(
            source="lever",
            external_id=j["id"],
            company=company_display_name,
            title=(j.get("text") or "").strip(),
            location=(j.get("categories") or {}).get("location", ""),
            url=j.get("hostedUrl", ""),
            description=j.get("descriptionPlain") or j.get("descriptionBodyPlain") or "",
        )
        for j in data
    ]
