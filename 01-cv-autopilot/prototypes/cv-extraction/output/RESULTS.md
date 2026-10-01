# Résultat du prototype — extraction CV, 2026-08-14

## Comment ce test a été fait

Pas d'`ANTHROPIC_API_KEY` configuré à ce stade — le script `extract_cv.py`
existe et est prêt à tourner en vrai, mais pour valider la *qualité* de
l'extraction aujourd'hui sans attendre une clé API, le prompt exact du
script (`SCHEMA_INSTRUCTIONS`) a été exécuté manuellement par Claude, en ne
lisant que le texte brut extrait de `CV_Data_Analyst_Erman_Tagaintchuem.docx`
(fichier `sample_input/`, aucune connaissance extérieure au texte utilisée).
Résultat : `CV_Data_Analyst_Erman_Tagaintchuem.json` dans ce même dossier.

## Vérification — comparé aux données déjà validées dans `data-erman/cv_content.json`

| Champ | Source de vérité (`cv_content.json`) | Extraction | Résultat |
|---|---|---|---|
| Poste 1 (titre/entreprise/dates) | `job_1` | `experiences[0]` | ✅ identique caractère pour caractère |
| Poste 2 (titre/entreprise/dates) | `job_2` | `experiences[1]` | ✅ identique caractère pour caractère |
| Formation | `education` | `education[0]` | ✅ identique |
| Certification 1 & 2 | `certifications[0..1]` | `certifications[0..1]` | ✅ même contenu (structuré en `name`/`status` au lieu d'une chaîne unique — différence de forme, pas de fond) |
| Certification 3 (LogicMojo) | `certifications[2]` | `certifications[2]` | ⚠️ **incomplète** — voir ci-dessous |

## Ce qui marche

Sur tout ce qui est factuel et présent dans le document — postes, dates,
entreprises, diplôme, compétences groupées par catégorie, bullets du projet
personnel — l'extraction est fidèle à 100%, sans reformulation ni ajout.
Aucune invention détectée. Les données personnelles sensibles (nationalité,
Emirates ID) ont été correctement isolées dans `extraction_notes` plutôt
que traitées comme un champ à réutiliser tel quel — la règle "ne jamais
insérer automatiquement" a été respectée.

## Ce qui ne marche pas encore — un vrai plafond, pas un bug

`cv_content.json` décrit la certification LogicMojo avec un détail que le
CV source ne contient pas : *"covers supervised/unsupervised ML, deep
learning, NLP, transformers, RAG, LLMs"*. Ce détail n'existe nulle part dans
le texte du `.docx` — je (Claude) l'avais ajouté à l'époque parce qu'Erman
me l'avait dit en conversation, pas parce que c'était écrit sur son CV.
L'extraction automatisée ne pouvait pas le deviner, et c'est très bien
qu'elle ne l'ait pas fait — elle n'a pas inventé.

**Ce que ça confirme** : l'extraction automatique a un plafond dur, celui du
document fourni. Tout ce qu'un utilisateur sait sur lui-même mais n'a pas
écrit dans son CV existant restera invisible au système, sauf s'il le donne
ailleurs. C'est exactement pour ça que l'étape 2 de l'onboarding validée le
2026-08-14 inclut *"un champ libre optionnel pour ce qui manque au CV"* —
ce test le confirme en pratique, pas juste en théorie.

## Mise à jour — vrai appel API (2026-08-15, OpenRouter)

Rejoué pour de vrai via `extract_cv.py` (OpenRouter, `anthropic/claude-sonnet-4.5`
par défaut) — plus une exécution manuelle. Résultat quasi identique : mêmes
faits, même structure. Deux différences mineures, sans impact sur la
fidélité : le statut de la certification LogicMojo reformulé ("In progress"
au lieu de la citation complète des dates), et une nouvelle note signalant
que les dates 2026 du CV semblent "future-dated" — un faux positif inoffensif
(2026 est la date réelle actuelle, pas une erreur du document). Le fichier
`CV_Data_Analyst_Erman_Tagaintchuem.json` de ce dossier reflète maintenant
cette version réelle, pas la version manuelle d'origine.

## Verdict

**Brique 1 (extraction) validée sur la fidélité factuelle.** Prête à passer
en Phase 2 avec un vrai appel API pour confirmer le comportement à froid (un
vrai modèle, pas Claude en conversation directe) — mais le prompt et le
schéma tiennent la route. Reste à construire : brique 2 (adaptation par
rôle) et brique 3 (mots-clés de matching), chacune sur son propre prototype
isolé, testée avant d'être combinée au reste.
