# Modèle de données — Phase 2 (PostgreSQL)

> Schéma complet : [`schema.sql`](./schema.sql). Ce document explique le
> *pourquoi* de chaque choix — surtout là où on s'écarte d'une traduction
> littérale des fichiers actuels.

## Principe directeur

Chaque fichier `data-<client>/*` de la Phase 1 devient une table partagée,
isolée par `user_id`. Rien n'est réinventé côté vocabulaire métier — les
statuts de candidature dans `applications.status` sont exactement ceux déjà
listés dans `tracker-candidatures.md` ("Envoyé", "Vue", "Contacté par
recruteur"...), pas une nomenclature nouvelle à réapprendre.

## Correspondance fichier → table

| Fichier Phase 1 (`data-<client>/...`) | Table(s) Phase 2 |
|---|---|
| `profile.json` | `profiles` |
| `roles.json` | `roles` |
| `cv_content.json` → `job_1`/`job_2` | `experiences` |
| `cv_content.json` → `roles.<id>.job*_bullets` | `role_experience_bullets` |
| `cv_content.json` → `roles.<id>.project_*` | `role_projects` |
| `cv_content.json` → `education`/`certifications` | `profiles.education` / `profiles.certifications` (jsonb) |
| `cover-letters.md` | `roles.cover_letter_template` |
| CV `.docx` généré | `cv_files` |
| `discovery_watchlist.json` | `discovery_sources` (type `ats_*`) |
| `email_accounts.json` | `discovery_sources` (type `gmail`) |
| `imap_accounts.json` | `discovery_sources` (type `imap`) |
| `seen_postings.json` | contrainte `UNIQUE(user_id, source, external_id)` sur `postings` |
| `tracker-candidatures.md` | `applications` |
| `queue/<date>-<entreprise>-<titre>/` | `applications` (statut `queued`, contenu dans `storage_key`) |
| — (n'existait pas) | `cv_uploads`, `cv_upload_extractions`, `extracted_profile_drafts`, `draft_source_uploads` (onboarding) |

## Décisions qui méritent d'être expliquées

**Upload multi-CV à l'onboarding — jusqu'à 3, extraits séparément puis
fusionnés (décision du 2026-08-15).** Trouvaille du prototype de la brique 2
(`prototypes/role-adaptation/output/RESULTS.md`) : un seul CV uploadé ne
capture jamais qu'une fraction de ce qu'une personne sait sur elle-même —
Erman en a 17, chacun met en avant une facette différente. D'où la décision :

- **Plafond : 3 CV à l'onboarding, minimum 1**, avec possibilité d'en
  ajouter d'autres plus tard depuis le tableau de bord, sans que ça bloque
  la fin de l'onboarding. Pas illimité — un plafond bas garde l'onboarding
  rapide (promesse "quelques mouvements", voir "Vision" dans `PRODUCT.md`)
  et limite le coût en appels IA par nouvel utilisateur.
- **Extraction document par document, jamais concaténée.** La brique 1 a
  été testée et validée sur UN document à la fois — la garder ainsi plutôt
  que de lui donner plusieurs CV concaténés d'un coup, ce qui n'a jamais
  été testé et créerait un texte source confus (le même poste répété
  plusieurs fois avec des formulations différentes). D'où `cv_upload_extractions`
  : une ligne par upload, sortie brute de la brique 1, inchangée.
- **Une fusion explicite, pas silencieuse, produit UN SEUL draft à
  relire.** L'utilisateur ne doit pas relire N profils séparés (ça
  reproduirait la friction qu'on essaie d'éliminer) — une étape de fusion
  regroupe les expériences par (entreprise + dates qui se recoupent), fait
  l'union des bullets et compétences distinctes vues sur les différents
  documents, et écrit `extracted_profile_drafts` en une seule ligne par
  utilisateur (plus par upload — `cv_upload_id` a été retiré de cette
  table). `draft_source_uploads` trace quels documents ont nourri ce draft.
- **Les désaccords entre documents ne sont jamais tranchés
  automatiquement.** Si deux CV donnent un numéro de téléphone différent,
  ou un statut de certification différent, la fusion ne choisit pas à la
  place de l'utilisateur — elle écrit le désaccord dans
  `extracted_profile_drafts.conflicts` et l'écran de relecture obligatoire
  (déjà décidé le 2026-08-14) force un choix explicite. Cohérent avec le
  principe central du produit : jamais de contenu utilisé sans validation
  humaine sur ce qui le concerne.
- **Logique de fusion prototypée et validée (2026-08-15)** —
  `prototypes/cv-merge/`, testée sur deux vrais CV d'Erman qui décrivent les
  mêmes deux emplois et le même projet phare avec des angles différents
  (pipeline de données vs modèle de prédiction de churn) : reconnu comme un
  seul projet, fusionné en une entrée plus riche que chacun des deux
  documents pris seuls. Un désaccord injecté volontairement (téléphone,
  statut de certification) a été détecté et correctement laissé non résolu
  plutôt que deviné. Détail : `prototypes/cv-merge/output/RESULTS.md`.

**Un même poste, raconté différemment selon le rôle ciblé.**
Dans `cv_content.json`, `job_1`/`job_2` (titre, entreprise, dates) sont
partagés entre toutes les variantes de CV — seuls les bullets
(`job1_bullets`, `job2_bullets`) changent d'un rôle à l'autre. Le schéma
préserve exactement cette séparation : `experiences` (partagé) +
`role_experience_bullets` (par rôle). Modifier une date d'emploi une fois la
répercute partout ; modifier le texte pour un rôle ne touche aucun autre CV.

**`contact_line_1`/`contact_line_2` deviennent des champs structurés.**
Le fichier actuel stocke des lignes déjà formatées ("email | téléphone |
linkedin | github"). C'était un raccourci de Phase 1, correct pour un seul
utilisateur qui relit son propre CV — mais un formulaire d'onboarding ne
peut pas éditer une chaîne pré-jointe champ par champ. `profiles` a donc des
colonnes distinctes (`phone`, `linkedin_url`, `github_url`...), assemblées
en ligne de contact au moment de générer le `.docx`, pas stockées déjà
assemblées.

**La dédup n'est plus un fichier JSON relu à la main.**
`seen_postings.json` est remplacé par une contrainte `UNIQUE(user_id,
source, external_id)` sur `postings`. Ce n'est pas cosmétique : le bug
rencontré en Phase 1.5 (une même offre apparue deux fois dans un seul run
n'était pas détectée avant l'ajout explicite de `seen.add(key)` en cours de
boucle) devient structurellement impossible — la deuxième tentative
d'insertion échoue sur la contrainte, point.

**Les rôles ne sont plus une liste globale fixe de 17 entrées.**
En Phase 1, `roles.json` est une liste unique, taillée pour Erman. En Phase
2, `roles` est une table par utilisateur — chacun définit ses propres
variantes (5, 3, ou 20), cohérent avec la décision d'onboarding du
2026-08-14 ("cibles de rôle" choisies par chip, pas une liste imposée).

**`cover_letter_text` est figé au moment de l'envoi.**
La lettre réellement envoyée est copiée dans `applications.cover_letter_text`
au moment de l'envoi, jamais recalculée depuis `roles.cover_letter_template`
après coup — si l'utilisateur modifie son template plus tard, l'historique
des candidatures déjà envoyées ne doit pas changer rétroactivement.

## Tranché (2026-08-15) : les secrets (mots de passe IMAP, tokens Gmail)

`discovery_sources.credential_ref` est un **pointeur**, jamais le secret
lui-même — en Phase 1, ces secrets vivent dans `.env` (mot de passe IMAP) ou
dans des fichiers `gmail_token_*.json` gitignorés (refresh token OAuth), tous
deux hors du dépôt. Un backend multi-tenant ne peut pas reproduire ça avec
une seule variable d'environnement par utilisateur.

**Décision : chiffrement applicatif** (`backend/app/core/crypto.py`, Fernet
— AEAD symétrique authentifié, pas un simple XOR). Une clé unique
(`SECRET_ENCRYPTION_KEY`, jamais en DB, jamais dans le dépôt) chiffre chaque
secret avant écriture ; `credential_ref` stocke le texte chiffré. Testé en
réel : roundtrip chiffrement/déchiffrement correct, et une mauvaise clé est
rejetée proprement (`CryptoNotConfiguredError`) plutôt que de planter ou de
renvoyer une donnée corrompue silencieusement.

Écarté pour l'instant, pas pour toujours : un secrets manager dédié
(Infisical, Doppler, AWS Secrets Manager) reste une amélioration valable
avant une ouverture publique large — pas nécessaire pour une bêta privée,
où l'objectif est de rester simple sans sacrifier la sécurité de base.

## Ce que ce schéma ne couvre pas encore

- Authentification (table `sessions`/`refresh_tokens` si JWT avec révocation)
- Facturation (au-delà de `users.stripe_customer_id` — événements Stripe,
  historique de paiement)
- `beta_testers.json` reste hors DB pour l'instant — c'est un artefact de
  configuration Google Cloud Console (Test users), pas une donnée produit.
