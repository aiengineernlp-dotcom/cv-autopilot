"""Couche : Repository.

Fait : seul fichier autorisé à lire/parser data-<client>/cover-letters.md — extrait
les templates bruts (numéro, titre, texte) séparés par "## NN — Titre".
Ne fait jamais : remplir les [PLACEHOLDERS] (Service letter_service), décider quel
template utiliser pour quel rôle (Repository roles_repository + Service matching_service).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ..config import ClientConfig

SECTION_RE = re.compile(r"^##\s+(\d+)\s+—\s+(.+)$", re.MULTILINE)


@dataclass
class LetterTemplate:
    number: int
    title: str
    raw: str


def _path(client: ClientConfig) -> Path:
    return client.root / "cover-letters.md"


def load_templates(client: ClientConfig) -> dict[int, LetterTemplate]:
    text = _path(client).read_text(encoding="utf-8")
    matches = list(SECTION_RE.finditer(text))
    templates: dict[int, LetterTemplate] = {}
    for i, m in enumerate(matches):
        number = int(m.group(1))
        title = m.group(2).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].split("\n---\n")[0].strip()
        templates[number] = LetterTemplate(number=number, title=title, raw=body)
    return templates
