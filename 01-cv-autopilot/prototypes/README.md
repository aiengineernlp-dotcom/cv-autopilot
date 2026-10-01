# Prototypes

Scripts isolés, jamais branchés à `engine/` ni à `data-<client>/` en écriture
— servent à valider une idée avant de l'intégrer au produit, pas à être
utilisés en production tels quels. Un dossier par idée testée.

## `cv-extraction/`

Brique 1 des trois identifiées dans `PRODUCT.md` (2026-08-14, section
"Angle mort identifié") : CV brut uploadé → profil structuré, sans
intervention humaine. Résultat du premier test : `cv-extraction/output/RESULTS.md`.

## `role-adaptation/`

Brique 2 : profil de base (sortie de `cv-extraction/`) + rôle cible → CV
adapté. Testé le 2026-08-15 sur le profil Data Analyst d'Erman, ciblant
"ML / AI Engineer" — résultat : `role-adaptation/output/RESULTS.md`.

## `matching-keywords/`

Brique 3 : profil adapté (sortie de `role-adaptation/`) → mots-clés de
matching (équivalent du champ `keywords` de `roles.json`). Testé à
l'aveugle avec un vrai appel API le 2026-08-15, prompt resserré après un
premier test bruyant — validée. Résultat : `matching-keywords/output/RESULTS.md`.

## `cv-merge/`

Brique manquante identifiée le 2026-08-15 (décision d'onboarding multi-CV,
jusqu'à 3 documents) : fusionne plusieurs extractions séparées (sortie de
`cv-extraction/`) en un seul profil de base à relire. Testée sur deux vrais
CV d'Erman qui décrivent le même vécu avec des angles différents (même
projet raconté comme pipeline de données dans l'un, comme modèle de
prédiction de churn dans l'autre — reconnu comme UN SEUL projet, fusionné),
puis sur un désaccord injecté volontairement (numéro de téléphone,
statut de certification — les deux détectés, aucun deviné). Résultat :
`cv-merge/output/RESULTS.md`. Validée.
