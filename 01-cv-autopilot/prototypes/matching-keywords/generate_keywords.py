"""Prototype isolé — pas branché au produit.

Fait : prend une variante de CV adaptée à un rôle (sortie de
prototypes/role-adaptation/adapt_role.py) et génère la liste de mots-clés de
matching pour ce rôle — l'équivalent du champ "keywords" dans roles.json,
consommé tel quel par matching_service.py (titre pondéré 3x, description 1x,
correspondance par limite de mot). C'est la brique 3 des trois identifiées
dans PRODUCT.md (2026-08-14).

Ne fait pas : inventer un mot-clé pour une compétence absente du profil
adapté, même plausible pour ce rôle (règle identique aux briques 1 et 2).
Applique aussi deux règles propres à cette brique. La première, tirée de
vrais bugs trouvés en Phase 1.5 (voir PRODUCT.md, "startup" qui matchait du
texte générique Stripe, "geo" qui matchait "Geotechnical") : préférer des
mots-clés à fort signal à des termes granulaires (noms d'algorithmes,
outils secondaires) qui ajoutent du bruit sans ajouter de rappel utile. La
deuxième, ajoutée le 2026-08-15 après un premier test à l'aveugle
(`output/RESULTS.md`) qui a montré une liste trop généreuse comparée à la
curation minimaliste de référence : exclure aussi les langages/frameworks/
outils à usage général (Python, SQL, Git, Django, Flask...) sauf si le rôle
cible EST spécifiquement ce langage/framework — ce ne sont pas des
inventions, mais ils diluent la précision du matching en apparaissant dans
la moitié des offres tech, peu importe leur pertinence réelle.

Utilisation :
    export OPENROUTER_API_KEY=sk-or-...
    python3 generate_keywords.py sample_input/adapted_profile.json

Sans OPENROUTER_API_KEY : voir output/RESULTS.md pour le résultat déjà
produit manuellement le 2026-08-15, en attendant — avec une mise en garde
sur un biais méthodologique à corriger lors du vrai test API (voir ce fichier).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _openrouter import call_llm  # noqa: E402

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
  "keywords": ["string — la liste finale, prête à coller dans roles.json"],
  "excluded_unsupported": [{"term": "string", "reason": "string"}],
  "excluded_too_granular": [{"term": "string", "reason": "string"}],
  "excluded_too_generic": [{"term": "string", "reason": "string"}]
}

Pas de texte avant ou après le JSON. Pas de markdown fences."""


def generate(adapted_profile: dict) -> dict:
    user_content = f"Profil adapté (JSON) :\n{json.dumps(adapted_profile, ensure_ascii=False)}"
    return call_llm(SYSTEM_PROMPT, user_content, max_tokens=2048)


def main():
    if len(sys.argv) != 2:
        print("Usage : python3 generate_keywords.py <profil_adapte.json>", file=sys.stderr)
        sys.exit(1)

    adapted_profile = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    result = generate(adapted_profile)

    input_path = Path(sys.argv[1])
    output_path = Path(__file__).parent / "output" / f"{input_path.stem}_keywords.json"
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Mots-clés générés -> {output_path}")


if __name__ == "__main__":
    main()
