"""Couche : Adapter.

Fait : seul fichier qui connaît l'API publique Greenhouse Job Board
(boards-api.greenhouse.io) — récupère les offres publiées par une entreprise,
normalise en Posting. API publique faite pour être consultée par des outils
externes — aucune violation de CGU (contrairement au scraping LinkedIn/Indeed,
qui reste interdit).
Ne fait jamais : décider si une offre correspond au profil (Service
matching_service), enregistrer quoi que ce soit sur disque (Repository).
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
