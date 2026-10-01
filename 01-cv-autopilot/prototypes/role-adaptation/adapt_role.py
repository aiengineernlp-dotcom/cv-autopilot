"""Prototype isolé — pas branché au produit.

Fait : prend un profil de base (sortie de prototypes/cv-extraction/extract_cv.py)
et un rôle cible, et produit une variante de CV adaptée à ce rôle — bullets
reformulés/sélectionnés/réordonnés pour l'emphase, jamais un fait nouveau.
C'est la brique 2 des trois identifiées dans PRODUCT.md (2026-08-14) :
"Adaptation par rôle — profil de base + rôle visé → bullets/summary différents".

Ne fait pas : inventer un outil, une métrique ou une réalisation absente du
profil de base — c'est la règle la plus importante de ce prompt, et le
prototype existe justement pour vérifier qu'elle tient (voir output/RESULTS.md).
Ne fait pas non plus la génération des mots-clés de matching (brique 3, pas
encore prototypée).

Utilisation :
    export OPENROUTER_API_KEY=sk-or-...
    python3 adapt_role.py sample_input/base_profile.json "ML / AI Engineer"

Sans OPENROUTER_API_KEY : voir output/RESULTS.md pour le résultat déjà
produit manuellement le 2026-08-14, en attendant.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _openrouter import call_llm  # noqa: E402

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
  "key_project": {"title": "string", "bullets": ["string"]},
  "coverage_notes": ["string — écarts entre le rôle cible et le profil de base, à combler par l'utilisateur"]
}

Pas de texte avant ou après le JSON. Pas de markdown fences."""


def adapt(base_profile: dict, target_role: str) -> dict:
    user_content = (
        f"Rôle cible : {target_role}\n\n"
        f"Profil de base (JSON) :\n{json.dumps(base_profile, ensure_ascii=False)}"
    )
    return call_llm(SYSTEM_PROMPT, user_content)


def main():
    if len(sys.argv) != 3:
        print('Usage : python3 adapt_role.py <profil_de_base.json> "<Rôle cible>"', file=sys.stderr)
        sys.exit(1)

    base_profile = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    target_role = sys.argv[2]
    result = adapt(base_profile, target_role)

    slug = target_role.lower().replace(" ", "_").replace("/", "_")
    output_path = Path(__file__).parent / "output" / f"{slug}.json"
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Variante adaptée -> {output_path}")


if __name__ == "__main__":
    main()
