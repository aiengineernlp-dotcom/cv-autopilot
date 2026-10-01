# Résultat du prototype — adaptation par rôle, 2026-08-15

## Comment ce test a été fait

Même méthode que la brique 1 : pas d'`ANTHROPIC_API_KEY` configuré, donc le
prompt exact du script (`SYSTEM_PROMPT`) a été exécuté manuellement par
Claude. **Entrée volontairement limitée** : uniquement la sortie de la
brique 1 (`sample_input/base_profile.json`, extraite du seul CV "Data
Analyst" d'Erman) — pas de connaissance extérieure, pas d'accès aux autres
CV existants ni aux conversations passées. Rôle cible : "ML / AI Engineer".
Résultat : `ml_ai_engineer.json` dans ce même dossier.

Ce choix (limiter l'entrée à une seule source) est délibéré : c'est
exactement la situation d'un nouvel utilisateur qui uploade un seul CV à
l'onboarding, pas 17 comme Erman en a accumulé pour ce produit.

## Vérification — comparé au `ml-ai-engineer` déjà validé dans `cv_content.json`

| Élément | Version prototype (base = 1 seul CV) | Version réelle (`cv_content.json`) | Écart |
|---|---|---|---|
| Postes, dates, entreprises | Identiques | Identiques | Aucun |
| Bullets job 1 (pipeline, feature engineering, EDA) | Reformulés avec la même emphase | Reformulés avec la même emphase | Convergent — même sélection de faits |
| Bullets job 2 | Repris fidèlement | Repris fidèlement + une phrase de liaison ("infrastructure plus tard réutilisée pour le travail ML") | La version réelle ajoute une phrase interprétative, pas une citation directe des faits sources |
| Titre du projet clé | "E-commerce Data Pipeline & Feature Engineering Framework" | "Customer Churn Prediction" | **Écart majeur — voir ci-dessous** |
| Compétences ML classique (Scikit-learn, Random Forest...) | Reprises telles quelles | Reprises telles quelles | Aucun |
| Compétences Deep Learning / NLP / LLM (PyTorch, TensorFlow, Transformers, LangChain...) | **Absentes, explicitement signalées comme non couvertes** | Présentes, en détail | **Écart majeur — voir ci-dessous** |

## Ce qui marche

Sur tout ce qui est réellement présent dans le profil de base, l'adaptation
reformule et réordonne fidèlement — même sélection de faits, même emphase,
sans reformuler au point de trahir le sens original. Le nombre "86 features"
a été correctement recalculé (81 automatiques + 5 manuelles, deux chiffres
déjà présents séparément dans la source) — un calcul, pas une invention.

## Les deux écarts, et pourquoi ils sont de bons résultats, pas des échecs

**1. Le projet "Customer Churn Prediction" n'a pas pu être reconstruit.**
La version réelle présente DataSphere360 comme un modèle de prédiction de
churn (Logistic Regression, Scikit-learn). Le CV "Data Analyst" utilisé
comme seule source ne mentionne ni churn, ni Logistic Regression, ni aucune
modélisation appliquée sur ce projet — seulement de la préparation de
données. Cette information existe ailleurs chez Erman (probablement une
conversation, ou un autre document), pas dans le CV donné en entrée.
**L'adaptation a correctement refusé d'inventer un modèle ML qui n'était
pas dans sa source** — exactement le comportement attendu de la règle 1
du prompt.

**2. Les compétences Deep Learning/NLP/LLM n'ont pas pu être reconstruites.**
Même cause : zéro mention de PyTorch, TensorFlow, Transformers, HuggingFace
ou LangChain dans le CV "Data Analyst" source. La certification LogicMojo
laisse deviner que ce contenu existe dans la formation en cours d'Erman —
mais ce même manque avait déjà été détecté et signalé lors du test de la
brique 1 (`prototypes/cv-extraction/output/RESULTS.md`). **Les deux
prototypes propagent la même honnêteté plutôt que de compenser l'un pour
l'autre** : brique 1 n'invente pas le détail manquant, brique 2, construite
sur la sortie de brique 1, n'invente pas non plus les compétences qui en
auraient dépendu. C'est le comportement système qu'on veut : les erreurs ne
s'accumulent pas, l'honnêteté se propage.

## Une conclusion produit concrète, pas juste technique

Les deux écarts ont la même cause racine : **un seul CV ne suffit pas à
capturer tout ce qu'une personne sait sur elle-même.** Erman a 17 CV
différents parce que chacun met en avant une facette différente de la même
expérience — un seul document n'en contient jamais qu'une fraction.

Ça confirme une idée déjà notée dans `PRODUCT.md` (le champ libre
complémentaire à l'onboarding) et en renforce une autre, mentionnée dans la
discussion externe synthétisée le 2026-08-14 : **permettre l'upload de
plusieurs CV existants à l'onboarding, pas un seul**, pour que le profil de
base parte d'un ensemble de faits plus complet avant même la première
adaptation. À ajouter explicitement à la décision d'onboarding.

## Mise à jour — vrai appel API (2026-08-15, OpenRouter)

Rejoué pour de vrai via `adapt_role.py` (`ml_ai_engineer_real_api.json`),
entrée = la sortie réelle de la brique 1 (pas la version manuelle). Résultat
cohérent avec le test manuel, en mieux sur un point : `coverage_notes` est
nettement plus détaillé (8 catégories d'écarts précises — Deep Learning,
NLP, Computer Vision, MLOps, Cloud ML, architectures de modèles, Big Data,
déploiement — au lieu de 3 notes génériques) et n'a toujours inventé aucun
outil absent du profil de base. Confirme que la discipline anti-invention
tient avec un vrai modèle, pas seulement quand c'est moi qui applique le
prompt à la main.

Un deuxième test a aussi été fait sur un rôle différent ("Data Engineer",
`data_engineer.json`) pour préparer un test à l'aveugle de la brique 3 —
voir `matching-keywords/output/RESULTS.md`.

## Verdict

**Brique 2 (adaptation) validée sur la fidélité et la discipline
anti-invention.** Le mécanisme fonctionne exactement comme prévu : il
reformule ce qu'il a, et refuse d'inventer ce qu'il n'a pas — en le
signalant plutôt qu'en le cachant (`coverage_notes`). Reste : brique 3
(mots-clés de matching par rôle), et une décision produit à prendre sur
l'upload multi-CV à l'onboarding.
