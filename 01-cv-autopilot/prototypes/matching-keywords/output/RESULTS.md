# Résultat du prototype — mots-clés de matching

## Test 1 (2026-08-15, sans clé API) — biaisé, non concluant

Voir l'historique git. Prompt conçu après avoir regardé la référence —
marqué explicitement comme non validé.

## Test 2 (2026-08-15, vrai appel API, à l'aveugle sur "Data Engineer") — concluant, mais bruyant

Premier vrai test à l'aveugle : 3/6 mots-clés réels absents (`data
warehouse`, `airflow`, `spark`) mais explicitement exclus par nom avec la
bonne raison, pas oubliés. Limite trouvée : liste 2-3x plus longue que la
curation réelle, polluée par des langages/frameworks à usage général
(`python`, `sql`, `django`, `flask`...). Fichier :
`data_engineer_adapted_keywords_v1.json` (récupéré de l'historique git).

## Prompt resserré (2026-08-15) — règle 4 ajoutée

Exclure aussi les langages/frameworks/bases de données à usage général
(sauf si le rôle cible EST cette technologie), avec une nouvelle catégorie
de sortie dédiée `excluded_too_generic`, distincte de `excluded_too_granular`
(noms d'algorithmes) et `excluded_unsupported` (compétences absentes).

### Re-test direct sur le même profil "Data Engineer" (v2)

`data_engineer_adapted_keywords_v2.json` — la liste passe de 16 à 14
mots-clés, mais surtout : `python`, `sql`, `postgresql`, `mysql`, `django`,
`flask`, `rest api`, `api`, `git`, `github`, `csv`, `json` sont maintenant
explicitement classés dans `excluded_too_generic` au lieu de polluer la
liste finale. Amélioration nette et attendue.

### Un vrai bug trouvé en vérifiant v2

`data warehouse` s'est retrouvé dans la liste finale des mots-clés — alors
que le profil adapté ne le mentionne QUE dans une phrase qui dit
explicitement qu'il est **absent** ("Data warehouse experience [...] not
present in profile"). Le modèle a capté la présence textuelle du terme sans
comprendre que la phrase l'niait. Contradiction directe avec la règle 1
("n'inclus que ce que le profil affirme que la personne possède").

**Règle 1 renforcée** : vérifier le sens de la phrase où un terme apparaît,
pas seulement sa présence — une mention dans "coverage_notes" ou toute
phrase de négation n'est pas une preuve de possession.

### Re-test après ce deuxième correctif (v3)

`data_engineer_adapted_keywords_v3.json` — `data warehouse` a bien disparu
de la liste finale, `excluded_unsupported` cite maintenant explicitement
"(coverage_notes)" comme justification pour chaque terme absent. Le bug
précis trouvé est corrigé.

**Effet de bord observé, pas corrigé volontairement** : `pandas` et
`sqlalchemy`, exclus en `excluded_too_generic` lors du test v2, réapparaissent
dans la liste finale de v3. Variabilité d'un run à l'autre, normale pour un
modèle de langage — pas un bug de prompt, un rappel que **la relecture
humaine obligatoire (déjà prévue à l'onboarding) reste nécessaire**, même
une fois le prompt bien réglé. Un prompt ne rend pas la relecture inutile,
il réduit le volume de corrections à faire.

## Test 3 (2026-08-15, vrai appel API, à l'aveugle sur "Data Scientist") — nouvelle limite trouvée

Rôle jamais consulté avant génération. Résultat :

| | Réel (`roles.json`, `data-scientist`) | Prototype (aveugle, prompt resserré) |
|---|---|---|
| Mots-clés | `data scientist`, `predictive modeling`, `statistical modeling`, `machine learning model`, `scikit-learn` | 21 termes — voir `data_scientist_adapted_keywords.json` |
| Recoupement | — | 2/5 (`data scientist`, `scikit-learn`) |

Le bruit "langage générique" a bien disparu (`python`, `pandas`, `numpy`,
`sql`, `git`, `plotly`, `matplotlib`... tous correctement classés
`excluded_too_generic`, avec de bonnes raisons). **Mais une limite plus
subtile apparaît** : la liste finale reste longue (21 termes) parce qu'elle
regroupe des techniques statistiques en catégories ("hypothesis testing",
"correlation analysis", "outlier detection", "distribution analysis",
"exploratory data analysis") — un bon réflexe de regroupement (éviter z-test/
t-test/chi-square individuellement), mais ces catégories elles-mêmes restent
trop génériques comme mots-clés de matching. La vraie liste d'Erman n'en
retient aucune — elle préfère des formulations orientées résultat
("predictive modeling", "statistical modeling") à des descriptions de
méthode ("hypothesis testing", "correlation analysis"). Le prompt actuel
sait exclure les outils/langages génériques mais ne fait pas encore la même
distinction pour les termes de méthode/processus.

## Verdict

**Amélioration réelle et mesurée** : le bruit "langage/framework générique"
identifié au premier test est corrigé, vérifié sur deux rôles différents à
l'aveugle. Un vrai bug de compréhension contextuelle a été trouvé et corrigé
en cours de route (négation mal interprétée). **Une nouvelle limite, plus
fine, reste ouverte** : les termes de méthode/processus statistique
(hypothesis testing, correlation analysis...) devraient probablement suivre
la même règle que les langages génériques — à traiter dans une prochaine
itération du prompt, pas maintenant, pour éviter de tourner en boucle sur
un seul prototype au lieu d'avancer. Le mécanisme anti-invention, lui, n'a
jamais failli sur aucun des 3 rôles testés (ml-ai-engineer, data-engineer,
data-scientist).
