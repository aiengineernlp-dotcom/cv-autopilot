"""Couche : infrastructure LLM -- un seul endroit qui sait parler à OpenRouter.
Port direct de prototypes/_openrouter.py (validé sur les 4 briques
d'onboarding, voir prototypes/*/output/RESULTS.md) -- même logique,
`settings` au lieu de variables d'environnement lues à la volée.
Ne fait jamais : connaître un prompt ou un schéma métier -- ça reste dans
les Services (cv_extraction_service, cv_merge_service, etc.)."""
from __future__ import annotations

import json

from openai import OpenAI

from ..config import settings


class LlmNotConfiguredError(RuntimeError):
    """OPENROUTER_API_KEY manquant -- erreur métier, pas une exception technique brute."""


class LlmResponseError(RuntimeError):
    """Réponse du modèle non exploitable (JSON invalide, souvent tronqué par
    max_tokens trop bas -- vécu en réel le 2026-08-15 sur la brique mots-clés).
    Erreur métier explicite plutôt qu'un JSONDecodeError brut qui remonte
    comme une 500 opaque côté API."""


def call_llm(system_prompt: str, user_content: str, *, max_tokens: int = 4096) -> dict:
    if not settings.openrouter_api_key:
        raise LlmNotConfiguredError("OPENROUTER_API_KEY manquant dans .env")

    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=settings.openrouter_api_key)
    response = client.chat.completions.create(
        model=settings.openrouter_model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
    )
    raw = response.choices[0].message.content
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end != -1:
            try:
                return json.loads(raw[start:end + 1])
            except json.JSONDecodeError:
                pass
        raise LlmResponseError(
            f"Réponse du modèle non-JSON ou tronquée (max_tokens={max_tokens} probablement trop bas) : {raw[:200]}..."
        )
