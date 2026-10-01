"""Couche : Service -- brique 2 de l'onboarding (adaptation par rôle). Port de
prototypes/role-adaptation/adapt_role.py, validé sur un vrai profil le
2026-08-15 (prototypes/role-adaptation/output/RESULTS.md), avec le même
changement "key_project" -> "key_projects" que cv_extraction_service (voir
son docstring) pour rester cohérent avec la sortie de la fusion.
Ne fait jamais : écrire en base (délègue au Repository appelant)."""
from __future__ import annotations

import json

from ..core.llm import call_llm

SYSTEM_PROMPT = """Tu adaptes un profil professionnel de base vers une variante de CV taillée
pour un rôle cible précis. Règles non négociables :

1. Tu ne peux QUE reformuler, sélectionner, réordonner ou changer l'emphase
   des faits déjà présents dans le profil de base fourni. Jamais ajouter un
   outil, une technologie, une métrique ou une réalisation qui n'y figure
   pas explicitement — même si elle semblerait plausible pour ce rôle.
2. Un nombre calculé à partir de deux nombres déjà présents (ex: une somme)
   est acceptable. Une compétence, un résultat ou un projet non mentionné
   dans le profil de base ne l'est jamais, quelle que soit sa plausibilité.
2bis. Le "rôle cible" est parfois un texte long et détaillé (une offre
   d'emploi entière collée telle quelle, pas juste un titre de poste) --
   il contient ses propres tâches, outils et exigences qui ne sont PAS des
   faits sur la personne. Ne laisse JAMAIS un terme ou une tâche du texte
   du rôle cible se glisser dans un bullet ou une compétence sous prétexte
   qu'il ressemble ou complète naturellement une tâche déjà présente dans
   le profil de base (ex: le profil dit "restocked amenities and linens",
   l'offre mentionne "restocking mini-bars" -- n'écris JAMAIS "restocked
   amenities, mini-bar items and linens", le mini-bar n'est pas un fait
   du profil, juste une exigence de l'offre). En cas de doute sur si un
   terme vient du profil ou de l'offre, exclus-le.
3. Si le rôle cible demande des compétences ou une expérience que le profil
   de base ne couvre pas, ne comble PAS le vide — liste-le explicitement
   dans "coverage_notes". C'est une information utile (écart de compétences
   réel), pas un échec du profil.
4. Réponds UNIQUEMENT avec un objet JSON valide respectant ce schéma :

{
  "title": "string (nom du rôle cible)",
  "summary": "string (2-4 phrases, uniquement des faits du profil de base)",
  "experiences": [
    {"position_title": "string (repris du profil de base)", "tailored_bullets": ["string"]}
  ],
  "skills": [{"category": "string", "items": ["string"]}],
  "key_projects": [{"title": "string", "subtitle": "string", "year": "string", "bullets": ["string"]}],
  "coverage_notes": ["string — écarts entre le rôle cible et le profil de base, à combler par l'utilisateur"]
}

Pas de texte avant ou après le JSON. Pas de markdown fences."""


def adapt(base_profile: dict, target_role: str) -> dict:
    user_content = (
        f"Rôle cible : {target_role}\n\n"
        f"Profil de base (JSON) :\n{json.dumps(base_profile, ensure_ascii=False)}"
    )
    return call_llm(SYSTEM_PROMPT, user_content)
