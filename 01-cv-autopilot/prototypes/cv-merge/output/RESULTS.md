# Résultat du prototype — fusion multi-CV, 2026-08-15

## Comment ce test a été fait

Vrai appel API (OpenRouter), pas de simulation manuelle. Entrée : deux
vraies extractions (brique 1, elle-même déjà validée), produites à partir
de deux vrais CV d'Erman qui décrivent **les mêmes deux emplois** avec des
angles très différents :

- `extraction_1_data_analyst` — CV "Data Analyst", projet DataSphere360
  présenté comme un framework de pipeline de données (pas de modélisation
  ML mentionnée)
- `extraction_2_ml_ai_engineer` — CV "ML/AI Engineer", même projet
  DataSphere360 présenté comme un modèle de prédiction de churn (Logistic
  Regression, Scikit-learn), plus un second projet absent du premier CV
  (CO2 Emission Tracker)

Cas volontairement difficile : deux documents qui parlent du même vécu,
mais dont aucun des deux, pris seul, ne montre l'image complète — exactement
le problème que l'upload multi-CV doit résoudre.

## Test 1 — fusion de deux vrais documents cohérents entre eux

Résultat : `merged_profile.json`. Points clés :

- **Les deux emplois ont été reconnus comme identiques** (même entreprise,
  mêmes dates) et fusionnés en une seule entrée chacun, bullets unis sans
  doublon — le job 1 réunit maintenant les détails pipeline/dashboard du
  premier CV ET le détail du modèle de churn du second.
- **Le cas le plus dur a été bien géré** : DataSphere360 est reconnu comme
  **un seul projet** malgré un titre différent et un angle très différent
  entre les deux CV (framework de données vs modèle de prédiction) — fusionné
  en une seule entrée qui contient maintenant les deux facettes. C'est
  exactement la valeur qu'on cherchait : le profil fusionné est plus riche
  que n'importe lequel des deux CV pris isolément.
- **CO2 Emission Tracker**, présent seulement dans le second CV, a été
  ajouté comme deuxième entrée séparée dans `key_projects` — pas fusionné à
  tort avec DataSphere360, pas perdu non plus.
- **Aucune invention détectée** en relisant bullet par bullet — chaque
  phrase du résultat se retrouve, telle quelle ou légèrement recomposée,
  dans l'un des deux documents sources.
- `conflicts` vide — attendu, ces deux vrais documents ne se contredisent
  sur rien (même téléphone, même email, mêmes dates de diplôme).

## Test 2 — désaccord injecté volontairement, pour vérifier le chemin non testé par le test 1

Le test 1 ne prouve pas que les vrais désaccords sont bien détectés,
puisqu'il n'y en avait aucun. Pour vérifier ce chemin sans attendre d'avoir
deux vrais CV contradictoires sous la main : copie de `extraction_2` avec
un numéro de téléphone différent et un statut de certification IBM changé
en "Completed" (l'original dit "In progress"). Résultat :
`merged_profile_conflict_test.json`.

- Les **deux désaccords injectés ont été détectés**, listés dans
  `conflicts` avec les deux valeurs concurrentes et leur document source,
  `resolved: null`.
- **Le champ `contact.phone` du profil fusionné est resté vide (`null`)** —
  le système n'a pas deviné, n'a pas pris la valeur d'un document au
  hasard. C'est le comportement le plus important à vérifier, et il tient.

## Verdict

**Fusion prototypée et validée**, sur un cas réel difficile (même vécu,
angles différents) et sur un cas de désaccord injecté. Les deux règles
critiques tiennent : union honnête des faits complémentaires sans les
traiter comme des doublons ni des contradictions, et aucune décision
silencieuse sur un vrai désaccord. Les 4 briques du pipeline d'onboarding
(extraction, adaptation, mots-clés, fusion) sont maintenant toutes
prototypées et testées avec un vrai appel API.

Limite connue, pas encore testée : le comportement avec 3 documents
(le plafond produit) plutôt que 2 — les deux tests ci-dessus n'utilisent
que 2 CV. À vérifier avant intégration si ça devient pertinent.
