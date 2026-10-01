"""Couche : helper partagé entre les 3 scripts de prototypes/ — pas branché
au produit (voir prototypes/README.md).

Fait : un seul point d'appel vers OpenRouter (API compatible OpenAI),
utilisé par cv-extraction/, role-adaptation/ et matching-keywords/ pour ne
pas dupliquer la logique client trois fois.
Ne fait jamais : lire un fichier de data-<client>/, prendre une décision
métier — chaque script reste responsable de son propre prompt et schéma.
"""
from __future__ import annotations

import json
import os
import sys


def call_llm(system_prompt: str, user_content: str, *, max_tokens: int = 4096) -> dict:
    """Appelle OpenRouter, renvoie la réponse déjà parsée en dict JSON.
    Quitte proprement avec un message clair si la clé ou le package manquent."""
    try:
        import openai
    except ImportError:
        print("⚠️  Le package 'openai' n'est pas installé (pip install openai).", file=sys.stderr)
        sys.exit(1)

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("⚠️  OPENROUTER_API_KEY manquant dans .env. Clé sur https://openrouter.ai/keys",
              file=sys.stderr)
        sys.exit(1)

    model = os.environ.get("OPENROUTER_MODEL", "anthropic/claude-sonnet-4.5")

    client = openai.OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
    response = client.chat.completions.create(
        model=model,
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
        # Certains modèles enveloppent parfois la réponse malgré la consigne
        # -- on tente d'extraire le premier bloc { ... } avant d'abandonner.
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end != -1:
            return json.loads(raw[start:end + 1])
        raise
