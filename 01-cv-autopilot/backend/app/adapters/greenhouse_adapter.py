"""Couche : Adapter. Copie de ../engine/adapters/greenhouse_adapter.py --
API publique (boards-api.greenhouse.io), faite pour être consultée par des
outils externes, aucune violation de CGU (contrairement au scraping
LinkedIn/Indeed, toujours exclu).

**Limite connue** : appel HTTP synchrone (`requests`) dans un service
autrement async -- bloque le thread du worker le temps de la requête (~1s).
Acceptable pour une bêta privée à faible concurrence ; à passer en tâche de
fond avant de scaler (voir backend/README.md).
Ne fait jamais : décider si une offre correspond au profil (matching_service),
écrire en base (Repository).
"""
from __future__ import annotations

import html
import re

import requests

from .posting import Posting

ENDPOINT = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(raw: str) -> str:
    text = TAG_RE.sub(" ", raw or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def fetch(board_token: str, company_display_name: str) -> list[Posting]:
    resp = requests.get(ENDPOINT.format(token=board_token), params={"content": "true"}, timeout=20)
    resp.raise_for_status()
    jobs = resp.json().get("jobs", [])
    return [
        Posting(
            source="greenhouse",
            external_id=str(j["id"]),
            company=company_display_name,
            title=(j.get("title") or "").strip(),
            location=(j.get("location") or {}).get("name", ""),
            url=j.get("absolute_url", ""),
            description=_strip_html(j.get("content", "")),
        )
        for j in jobs
    ]
