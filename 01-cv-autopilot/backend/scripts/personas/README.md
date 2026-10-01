# Personas de test — 10 postes

> Créé le 2026-08-16. Fixtures réutilisables pour tester la chaîne complète
> (login → rôle depuis une offre → CV → lettre de motivation → aperçu
> d'envoi) sur 10 métiers volontairement variés, pas seulement tech/corporate.

## Comment relancer ce test

Dans l'ordre, depuis `backend/` (venv activée, backend + Postgres locaux lancés) :

| Étape | Commande | Ce qu'elle fait |
|---|---|---|
| 0 | `python3 scripts/personas/0_create_accounts.py` | Ajoute les 10 emails à `beta_invites`, crée les 10 comptes via un vrai `POST /auth/signup`. Idempotent. |
| 1 | `python3 scripts/personas/1_seed_personas.py` | Fait passer chaque profil à l'état "confirmé" (comme un onboarding terminé), sans repayer les appels LLM d'extraction/fusion déjà validés ailleurs. |
| 2 | `python3 scripts/personas/2_run_persona_pipeline.py` | Pour chaque persona : crée le rôle depuis une offre réaliste collée (vrai LLM), génère le CV, crée une candidature, génère la lettre (vrai LLM), teste l'aperçu d'envoi. Écrit `persona_report.json` (non commité). |

`personas.json` contient les 10 profils + les 10 offres cibles (avec des exigences volontairement absentes des faits, pour tester que rien n'est inventé).

## Les 10 accès

Mot de passe identique pour les 10 : **`TestPersona123!`**

| # | Poste | Email | Domaine | Piège testé dans l'offre |
|---|---|---|---|---|
| 1 | Data Analyst | `test-data-analyst@cvautopilot.dev` | Tech/Data | Power BI / Tableau non maîtrisés |
| 2 | IT Support Engineer | `test-it-support@cvautopilot.dev` | Tech/IT | AWS + scripting Python/PowerShell non maîtrisés |
| 3 | SEO Specialist | `test-seo@cvautopilot.dev` | Marketing digital | Google Ads / PPC non maîtrisés |
| 4 | Real Estate Sales Consultant | `test-real-estate@cvautopilot.dev` | Immobilier | Licence RERA + vente indépendante non établies (bug trouvé et corrigé ici) |
| 5 | Registered Nurse - ICU | `test-nurse@cvautopilot.dev` | Santé | Service général confondu avec soins intensifs (bug trouvé et corrigé ici) |
| 6 | Front Desk Supervisor | `test-hotel@cvautopilot.dev` | Hôtellerie | Rôle non-supervisé présenté comme supervisé (à surveiller, pas un bug net) |
| 7 | Senior Accountant | `test-accountant@cvautopilot.dev` | Finance | Junior vs senior, pas de certification CPA/ACCA |
| 8 | Customer Service Team Lead | `test-customer-service@cvautopilot.dev` | Support client | Contributeur individuel vs lead d'équipe |
| 9 | Construction Site Supervisor | `test-construction@cvautopilot.dev` | BTP | Résidentiel vs commercial/high-rise, pas d'OSHA |
| 10 | Primary School Teacher (IB) | `test-teacher@cvautopilot.dev` | Éducation | Curriculum national vs IB PYP non maîtrisé |

## Résultat du dernier passage (2026-08-16)

10/10 : rôle créé, CV généré, lettre générée, aperçu d'envoi testé (404 attendu -- aucun compte email connecté sur ces personas, la mécanique de l'aperçu fonctionne, juste pas de compte pour aller plus loin).

9/10 lettres propres (aucune invention, écarts honnêtement assumés). 2 bugs réels trouvés en inspectant les lettres, tous deux corrigés dans `cover_letter_service.py` et revérifiés :
- **Immobilier** : la lettre affirmait être "actively working toward obtaining" la licence RERA -- jamais dit par la candidate.
- **Infirmière** : la lettre décrivait des patients de service général comme "critically ill patients" -- contamination du niveau de gravité depuis l'offre (poste en ICU).

## Ce qui n'est PAS testé ici

Découverte automatique (ATS/alertes email) — ces 10 métiers ne peuvent pas être trouvés via Greenhouse/Lever (limite connue, documentée dans `PRODUCT.md` : la découverte auto ne sert que les profils tech/corporate). Le flux "coller une offre précise" testé ici est justement le contournement prévu pour tous les autres métiers.
