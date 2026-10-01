"""Couche : Service -- brique 3 de l'onboarding (mots-clés de matching). Port
de prototypes/matching-keywords/generate_keywords.py, version resserrée et
validée à l'aveugle sur 2 rôles le 2026-08-15
(prototypes/matching-keywords/output/RESULTS.md).
Ne fait jamais : écrire en base (délègue au Repository appelant)."""
from __future__ import annotations

import json

from ..core.llm import call_llm

SYSTEM_PROMPT = """Tu génères la liste de mots-clés de matching pour une variante de CV adaptée
à un rôle. Ces mots-clés seront comparés au titre (poids fort) et à la
description (poids faible) de vraies offres d'emploi par correspondance de
limite de mot. Règles non négociables :

1. N'inclus un mot-clé lié à une compétence ou technologie QUE si le profil
   affirme que la personne la possède. Une mention dans "coverage_notes"
   (ou toute autre phrase du profil qui dit qu'une compétence est ABSENTE,
   non couverte, ou manquante) n'est PAS une preuve de possession — c'est
   la preuve du contraire. Vérifie le sens de la phrase où le terme
   apparaît, pas seulement sa présence textuelle. Jamais un mot-clé
   plausible pour ce rôle mais absent du profil, même si l'association
   semble évidente.
2. Les variantes du titre du rôle lui-même (synonymes de poste) sont
   toujours acceptables, même sans preuve dans le profil — c'est l'intitulé
   que l'utilisateur vise, pas une compétence à prouver.
3. Préfère des termes à fort signal (intitulés de poste, technologies
   phares réellement citées) à des termes granulaires (noms d'algorithmes,
   d'outils secondaires) — un mot-clé trop générique ou trop fréquent dans
   du texte non pertinent crée des faux positifs (ex. observé en
   production : "geo" matchait "Geotechnical Design Engineer", "startup"
   matchait le texte générique "who we are" de Stripe). En cas de doute,
   exclus plutôt qu'inclus.
4. Exclus aussi les langages, frameworks, bases de données et outils à
   usage général — Python, SQL, Java, Git, Django, Flask, React, MySQL,
   PostgreSQL, CSV/JSON, etc. — même s'ils sont réellement présents dans le
   profil. Exception : le rôle cible porte spécifiquement sur cette
   technologie (ex. "Python Developer" → "python" reste légitime). Objectif :
   une liste courte de termes qui distinguent VRAIMENT ce rôle des autres,
   pas un inventaire de tout ce que la personne sait faire.
5. Sépare explicitement ce que tu inclus de ce que tu exclus et pourquoi —
   trois catégories d'exclusion différentes : "non prouvé par le profil"
   (écart réel à combler par l'utilisateur), "prouvé mais trop granulaire"
   (nom d'algorithme/outil secondaire, choix de qualité de matching), et
   "prouvé mais trop générique" (langage/framework à usage général, dilue
   la précision).
6. Réponds UNIQUEMENT avec un objet JSON valide respectant ce schéma :

{
  "keywords": ["string — la liste finale, prête à coller dans roles.keywords"],
  "excluded_unsupported": [{"term": "string", "reason": "string"}],
  "excluded_too_granular": [{"term": "string", "reason": "string"}],
  "excluded_too_generic": [{"term": "string", "reason": "string"}]
}

Pas de texte avant ou après le JSON. Pas de markdown fences."""


def generate(adapted_profile: dict) -> dict:
    user_content = f"Profil adapté (JSON) :\n{json.dumps(adapted_profile, ensure_ascii=False)}"
    # 2048 s'est avéré trop court en test réel (2026-08-15) : le prompt resserré
    # (règle 4, catégorie excluded_too_generic) produit une réponse plus longue
    # que le prototype d'origine -- coupait le JSON en plein milieu.
    return call_llm(SYSTEM_PROMPT, user_content, max_tokens=4096)
