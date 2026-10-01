"""Couche : Service -- brique 1 de l'onboarding (extraction). Port de
prototypes/cv-extraction/extract_cv.py, validé sur un vrai CV le 2026-08-15
(prototypes/cv-extraction/output/RESULTS.md), avec UN changement délibéré :
"key_project" (singulier) devient "key_projects" (liste) -- le prototype
d'origine n'avait qu'un projet, mais la fusion (prototypes/cv-merge/) et la
table `role_projects` supportent plusieurs projets par profil. Corrigé ici
pour que les 4 briques utilisent le même schéma de bout en bout -- retesté
en réel après ce changement (voir backend/README.md, section onboarding).
Ne fait jamais : lire un fichier (délègue à core.storage), écrire en base
(délègue au Repository appelant)."""
from __future__ import annotations

from ..core.llm import call_llm

SCHEMA_INSTRUCTIONS = """Tu extrais un CV brut vers un profil structuré. Règles non négociables :

1. N'extrait QUE ce qui est écrit noir sur blanc dans le texte fourni. Jamais
   d'invention, jamais de déduction ("il a probablement aussi fait X"),
   jamais de reformulation qui ajoute un fait non présent dans le texte.
2. Si une information est ambiguë, incomplète, ou absente, laisse le champ
   vide ("" ou []) et explique pourquoi dans "extraction_notes" — ne devine
   jamais à sa place.
3. Signale explicitement dans "extraction_notes" toute donnée personnelle
   sensible présente dans le texte (nationalité, statut de visa, date de
   naissance...) — elle doit être confirmée par l'utilisateur avant d'être
   réutilisée où que ce soit, jamais insérée automatiquement dans un CV généré.
4. Réponds UNIQUEMENT avec un objet JSON valide respectant exactement ce schéma :

{
  "headline": "string",
  "contact": {
    "email": "string", "phone": "string", "linkedin_url": "string",
    "github_url": "string", "location": "string", "additional_notes": ["string"]
  },
  "summary": "string (copié tel quel, pas reformulé)",
  "experiences": [
    {"position_title": "string", "company_location": "string", "date_range": "string", "bullets": ["string"]}
  ],
  "education": [{"degree": "string", "institution": "string", "date": "string"}],
  "certifications": [{"name": "string", "status": "string"}],
  "skills": [{"category": "string", "items": ["string"]}],
  "key_projects": [{"title": "string", "subtitle": "string", "year": "string", "bullets": ["string"]}],
  "extraction_notes": ["string"]
}

Pas de texte avant ou après le JSON. Pas de markdown fences."""


def extract(cv_text: str) -> dict:
    return call_llm(SCHEMA_INSTRUCTIONS, f"Texte du CV :\n\n{cv_text}")
