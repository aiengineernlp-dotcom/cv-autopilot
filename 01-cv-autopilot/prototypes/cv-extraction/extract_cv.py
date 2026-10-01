"""Prototype isolé — pas branché au produit.

Fait : lit un CV brut (.docx ou .txt), envoie son texte à Claude avec un
prompt strict (n'extraire que ce qui est écrit, jamais inventer ni broder),
récupère un profil structuré en JSON, l'enregistre pour relecture humaine.
C'est la brique 1 des trois identifiées dans PRODUCT.md (2026-08-14) comme
angle mort avant la Phase 2 : "Extraction — CV brut → profil structuré".

Ne fait pas (volontairement, à ce stade) : l'adaptation par rôle (brique 2)
ni la génération de mots-clés de matching (brique 3) — un script à la fois,
validé avant de passer au suivant. Ne touche à aucun fichier de
data-erman/ : ce prototype est isolé, ses résultats vivent dans output/.

Utilisation :
    export OPENROUTER_API_KEY=sk-or-...
    python3 extract_cv.py sample_input/CV_Data_Analyst_Erman_Tagaintchuem.txt

Sans OPENROUTER_API_KEY : le script s'arrête proprement avec un message clair
(voir output/RESULTS.md pour le résultat déjà produit manuellement, sans
appel API, le 2026-08-14).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _openrouter import call_llm  # noqa: E402

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
  "key_project": {"title": "string", "subtitle": "string", "year": "string", "bullets": ["string"]},
  "extraction_notes": ["string"]
}

Pas de texte avant ou après le JSON. Pas de markdown fences."""


def read_text(path: Path) -> str:
    if path.suffix.lower() == ".docx":
        import docx  # python-docx, déjà dans requirements.txt

        doc = docx.Document(str(path))
        return "\n".join(p.text.strip() for p in doc.paragraphs if p.text.strip())
    return path.read_text(encoding="utf-8")


def extract(cv_text: str) -> dict:
    return call_llm(SCHEMA_INSTRUCTIONS, f"Texte du CV :\n\n{cv_text}")


def main():
    if len(sys.argv) != 2:
        print("Usage : python3 extract_cv.py <fichier_cv.docx|.txt>", file=sys.stderr)
        sys.exit(1)

    input_path = Path(sys.argv[1])
    cv_text = read_text(input_path)
    result = extract(cv_text)

    output_path = Path(__file__).parent / "output" / f"{input_path.stem}.json"
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Profil extrait -> {output_path}")


if __name__ == "__main__":
    main()
