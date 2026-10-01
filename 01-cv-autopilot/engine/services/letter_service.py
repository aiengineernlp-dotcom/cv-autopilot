"""Couche : Service (Logic Engine).

Fait : remplit un texte contenant des [PLACEHOLDERS] connus (lettre de motivation
ou relance J+7 — même logique pour les deux), signale ceux non résolus.
Ne fait jamais : lire cover-letters.md ou tracker-candidatures.md (Repositories),
envoyer l'email (Adapter resend_adapter).

Sécurité produit : le retour inclut toujours la liste des placeholders non résolus.
L'appelant (Service application_service / followup_service) doit refuser un envoi
automatique tant que cette liste n'est pas vide — jamais un texte avec des
[CROCHETS] envoyé en réel.
"""
from __future__ import annotations

import re

from ..repositories.cover_letter_repository import LetterTemplate

PLACEHOLDER_RE = re.compile(r"\[([^\]]+)\]")


def render_text(raw: str, placeholders: dict) -> tuple[str, list[str]]:
    text = raw
    for key, value in placeholders.items():
        text = text.replace(f"[{key}]", value)
    unresolved = sorted(set(PLACEHOLDER_RE.findall(text)))
    return text, unresolved


def render(template: LetterTemplate, placeholders: dict) -> tuple[str, list[str]]:
    return render_text(template.raw, placeholders)
