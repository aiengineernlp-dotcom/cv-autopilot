"""Couche : Service -- brique fusion de l'onboarding (upload multi-CV,
décision du 2026-08-15). Port direct de prototypes/cv-merge/merge_profiles.py,
validé sur deux vrais CV + un désaccord injecté (prototypes/cv-merge/output/RESULTS.md).
Ne fait jamais : écrire en base (délègue au Repository appelant)."""
from __future__ import annotations

import json

from ..core.llm import call_llm

SYSTEM_PROMPT = """Tu fusionnes plusieurs profils extraits séparément de différents CV de la
même personne en UN SEUL profil de base. Règles non négociables :

1. N'affirme que ce qui est écrit dans au moins un des documents fournis.
   Jamais un fait nouveau, même plausible.

2. Distingue deux situations très différentes :
   a) MÊME poste ou MÊME projet, décrit différemment selon le document
      (même entreprise + dates qui se recoupent ; ou même projet sous un
      titre différent avec des détails cohérents, pas contradictoires) —
      ce n'est PAS un désaccord, c'est une omission normale : un CV tait
      des détails hors-sujet pour le rôle qu'il cible. UNIS les bullets
      distincts des deux documents en une seule entrée, plus riche que
      chacun des documents pris isolément. Ne garde pas un doublon quasi
      identique reformulé deux fois — garde la version la plus précise.
   b) VRAIE contradiction factuelle (ex: deux numéros de téléphone
      différents, deux dates de diplôme différentes pour le même diplôme)
      — NE fusionne PAS, NE choisis PAS à la place de l'utilisateur.
      Liste-le dans "conflicts" avec les valeurs concurrentes et leur
      document source.

      Règles STRICTES sur "conflicts", pour que l'interface puisse
      appliquer un candidat en un clic sans deviner :
      - "field" est un chemin exact dans le JSON de sortie ci-dessous,
        en notation pointée avec index numérique entre crochets pour les
        tableaux (0-based) — ex: "contact.email", "experiences[1].date_range",
        "education[0].date", "skills[0].category". Jamais une description
        en langage naturel, jamais un chemin qui n'existe pas dans le JSON
        que tu produis.
      - UN SEUL conflit par "field" — si un champ composite (comme
        "date_range" = "Aug 2022 - Aug 2024") contient plusieurs
        sous-parties en désaccord (le début ET la fin diffèrent), c'est
        TOUJOURS un seul conflit sur ce field, jamais deux conflits
        séparés pour la même valeur de champ.
      - Chaque "value" candidat est la valeur COMPLÈTE que prendrait ce
        field si on le choisissait (ex: "Aug 2022 - Aug 2024", jamais
        juste "Aug 2022") — même si un seul mot diffère entre les
        documents, recopie le champ entier pour chaque candidat.

3. Les compétences (skills) sont unies par catégorie, dédupliquées par nom
   normalisé (pas de casse différente comptée deux fois).

4. Les projets sont unis dans une LISTE ("key_projects", pas un seul
   "key_project") — si deux documents décrivent le même projet sous-jacent
   avec des angles différents (cas 2a), une seule entrée enrichie ; s'ils
   décrivent deux projets réellement distincts, deux entrées séparées.

5. Réponds UNIQUEMENT avec un objet JSON valide respectant ce schéma :

{
  "headline": "string",
  "contact": {"email": "string", "phone": "string", "linkedin_url": "string",
              "github_url": "string", "location": "string", "additional_notes": ["string"]},
  "summary": "string",
  "experiences": [{"position_title": "string", "company_location": "string",
                    "date_range": "string", "bullets": ["string"]}],
  "education": [{"degree": "string", "institution": "string", "date": "string"}],
  "certifications": [{"name": "string", "status": "string"}],
  "skills": [{"category": "string", "items": ["string"]}],
  "key_projects": [{"title": "string", "subtitle": "string", "year": "string", "bullets": ["string"]}],
  "merge_notes": ["string — ce qui a été uni, et pourquoi ce n'était pas un désaccord"],
  "conflicts": [{"field": "string", "candidates": [{"value": "string", "source_document": "string"}], "resolved": null}]
}

Pas de texte avant ou après le JSON. Pas de markdown fences."""


def merge(extractions: list[dict], source_labels: list[str]) -> dict:
    labeled = [{"source_document": label, **extraction} for label, extraction in zip(source_labels, extractions)]
    user_content = f"Profils à fusionner (JSON, un par document source) :\n{json.dumps(labeled, ensure_ascii=False)}"
    return call_llm(SYSTEM_PROMPT, user_content)
