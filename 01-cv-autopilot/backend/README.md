# Backend — CV Autopilot (Phase 2)

FastAPI + PostgreSQL, isolé du CLI Phase 1 (`../engine/`) — même repo,
même produit, deux couches d'exécution différentes (voir `PRODUCT.md`).

## Architecture (même SoC que `../engine/`)

```
app/
  routers/       UI HTTP — parse la requête, appelle un Service, sérialise. Rien d'autre.
  services/      Logique métier — orchestre Repositories + core/security.
  repositories/  Seuls fichiers autorisés à faire une requête SQL sur une table donnée.
  models/        Miroir SQLAlchemy de docs/schema.sql — la forme des données, rien d'autre.
  schemas/       Contrat HTTP (Pydantic) — jamais les modèles SQLAlchemy exposés directement.
  core/          Sécurité (JWT, bcrypt) et dépendances FastAPI partagées.
```

`docs/schema.sql` (à la racine du produit) reste la source de vérité du
schéma — la migration initiale l'exécute directement plutôt que de le
retraduire en opérations Alembic (voir `alembic/versions/0001_initial_schema.py`).

## Installer et lancer en local

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Remplis `.env` :
- `DATABASE_URL` — par défaut pointe sur une base Postgres locale
- `JWT_SECRET_KEY` — génère avec `python3 -c "import secrets; print(secrets.token_hex(32))"`

### Base de données locale (macOS, Homebrew)

```bash
brew install postgresql@14
# si `brew services start` échoue (erreur launchctl en environnement sandboxé) :
pg_ctl -D /opt/homebrew/var/postgresql@14 -l /tmp/postgres_log.txt start
createdb cv_autopilot_dev
```

### Migrations

```bash
alembic upgrade head
```

### Lancer l'API

```bash
uvicorn app.main:app --reload --port 8000
```

Vérifie : `curl http://127.0.0.1:8000/health` → `{"status":"ok"}`

## Testé en réel (2026-08-15)

Signup → login → `/auth/me` avec le jeton, plus les cas d'échec (sans
jeton → 401, email déjà pris → 409, mauvais mot de passe → 401) — tous
vérifiés par de vraies requêtes HTTP contre une vraie base Postgres locale,
pas des mocks. Le profil associé (`profiles`) est bien créé en cascade à
l'inscription.

## Ce qui existe aujourd'hui

- `/health` — vérifie que l'API et la DB répondent
- `/auth/signup`, `/auth/login`, `/auth/me` — inscription, connexion (JWT), utilisateur courant
- **Onboarding, les 4 briques branchées (2026-08-15)** :
  - `POST /onboarding/cv-uploads` — upload un CV (.docx/.txt), extrait (brique 1), plafond de 3 par utilisateur
  - `GET /onboarding/cv-uploads` — liste les CV uploadés
  - `DELETE /onboarding/cv-uploads/{id}` — retire un CV (libère une place sous le plafond, demandé par l'utilisateur le 2026-08-15). Supprime le fichier physique et la ligne DB ; sans effet sur un profil déjà confirmé (les données utiles ont déjà été copiées dans `experiences`/`profiles` à la confirmation)
  - `DELETE /onboarding/profile` — vide les CV uploadés + le draft (actif ou confirmé) pour repartir de zéro à l'étape 1-2. Ne touche **jamais** aux rôles déjà créés (2026-08-15, voir `onboarding_service.reset_profile`)
  - `POST /onboarding/merge` — fusionne tous les CV extraits en un seul draft (brique fusion)
  - `GET /onboarding/draft` — le draft à relire
  - `PATCH /onboarding/draft` — soumet une relecture (résout les désaccords)
  - `POST /onboarding/draft/confirm` — confirme (bloqué si désaccords non résolus), matérialise `experiences` + `profiles`
  - `POST /onboarding/roles` — crée une variante de rôle **générique** (brique adaptation + brique mots-clés), écrit `role_experience_bullets`/`role_projects`/`roles.keywords`
  - `POST /onboarding/roles/from-posting` — adaptation par **offre précise** (2026-08-15) : `{title, company?, description}` où `description` est le texte complet d'une offre (collée par l'utilisateur, pas juste un nom de rôle). Réutilise `_adapt_and_persist_role` en interne, zéro changement de prompt nécessaire — `role_adaptation_service.adapt()` ne fait aucune différence entre un nom court et un texte d'offre entier. Voir "Adaptation par offre précise" plus bas pour le contexte produit et un bug d'hallucination trouvé et corrigé.
  - `GET /onboarding/roles` — liste les rôles créés
  - `DELETE /onboarding/roles/{id}` — supprime un rôle précis (et son `.docx` généré). Contrairement à `DELETE /onboarding/profile`, celle-ci est volontairement destructive pour le rôle visé (2026-08-15)

### Bug d'extraction .docx — tableaux ignorés (2026-08-15)

Signalé par l'utilisateur en testant avec un vrai modèle de CV téléchargé
en ligne ("Warehouse-Worker-Resume-Sample") : l'extraction renvoyait
"aucune expérience ni compétence identifiable" alors que le CV était bien
rempli. Cause : `storage.extract_text()` ne lisait que `doc.paragraphs`
-- tout texte placé dans un **tableau** (mise en page très répandue sur
les modèles de CV gratuits : colonne compétences/contact à gauche,
expérience à droite) était silencieusement ignoré. Reproduit avec un CV
de test à deux colonnes : seul "John Doe / Warehouse Worker" (les deux
seuls paragraphes hors tableau) était extrait, tout le contenu utile
vivait dans les cellules.

Corrigé : `_iter_docx_block_items()` parcourt paragraphes et tableaux
dans leur ordre réel d'apparition (motif standard python-docx, un niveau
de récursion dans les cellules -- tableaux imbriqués dans un tableau hors
périmètre, cas rare pour un CV). **Testé en réel** : même CV de test,
extraction complète (contact, compétences, certification, 2 expériences
avec bullets, formation) en local puis en production (l'effet du
déploiement a mis un peu de temps à se propager, deuxième `railway up`
nécessaire avant de voir le correctif appliqué -- vérifié en réextrayant
le même fichier après coup).

Ce bug touchait potentiellement une bonne partie des CV réels utilisant
des modèles gratuits en ligne (mise en page en tableau très commune) --
pas un cas limite rare.

### Onboarding testé en réel (2026-08-15)

Parcours complet exécuté avec de vraies requêtes HTTP, deux vrais CV
d'Erman (Data Analyst + ML/AI Engineer), et de vrais appels OpenRouter (pas
de simulation) : upload des 2 CV → fusion (a détecté 2 désaccords que le
test prototype n'avait pas trouvés — variabilité normale d'un LLM, pas un
bug) → confirmation bloquée tant que les désaccords ne sont pas résolus
(409, vérifié) → relecture soumise → confirmation réussie → `experiences`
et `profiles` matérialisés en base → création du rôle "ML / AI Engineer"
puis "Data Analyst" → `role_experience_bullets`/`role_projects` écrits
correctement pour les deux.

**Trois bugs réels trouvés et corrigés pendant ce test** :
1. `Mapped[datetime]` sans mapping explicite → colonnes `TIMESTAMPTZ`
   traitées comme naïves par SQLAlchemy, `confirm_draft` cassait avec
   "can't subtract offset-naive and offset-aware datetimes". Corrigé via
   `type_annotation_map` sur `Base` (voir `app/db.py`).
2. `max_tokens=2048` trop bas pour la brique mots-clés (le prompt resserré
   du 2026-08-15 produit une réponse plus longue) → JSON tronqué, erreur
   500 opaque. Monté à 4096, et `core/llm.py` lève maintenant une
   `LlmResponseError` explicite (502) au lieu de laisser fuiter une
   exception technique brute.
3. Le schéma `key_projects` de la brique adaptation avait perdu les champs
   `subtitle`/`year` en portant le prototype — `role_projects.year` restait
   vide en base. Corrigé, revérifié sur un deuxième rôle.

### Génération du CV final (2026-08-15)

- `POST /onboarding/roles/{role_id}/generate-cv` — construit le `.docx`
  (réutilise `app/cv_style.py`, copie de `../engine/cv_style.py` — voir son
  docstring), l'enregistre, crée une ligne `cv_files`, passe `roles.status`
  à `cv_ready`. Rappel de version à chaque régénération (`cv_files.version`).
- `GET /onboarding/roles/{role_id}/cv` — télécharge la dernière version.

**Testé en réel** : parcours complet upload → fusion (1 CV, pas de
désaccord) → confirmation → création de rôle → génération → téléchargement
→ fichier `.docx` réel (vérifié par `file`, valide Microsoft OOXML) →
relu avec `python-docx`, contenu conforme (sections dans le bon ordre,
bullets corrects, aucune section vide affichée). Deuxième génération sur le
même rôle → `version` passe bien à 2, `roles.status` confirmé `cv_ready`
en base.

**Différence assumée avec la Phase 1** : la Phase 2 supporte plusieurs
projets par rôle (`role_projects`, section "KEY PROJECTS" si plus d'un),
contre un seul en Phase 1. Les notes personnelles sensibles (nationalité,
statut de visa) présentes dans les CV sources ne sont **pas** reportées
dans le CV généré — `profiles` n'a pas de champ dédié pour ça
aujourd'hui (elles étaient déjà isolées dans `extraction_notes`/
`additional_notes` sans jamais être réutilisées automatiquement, voir
`docs/DATA_MODEL.md`) ; à trancher explicitement si on veut les rendre
disponibles un jour, pas un oubli silencieux.

### Adaptation par offre précise (2026-08-15)

Décision produit majeure de cette session : l'adaptation "par rôle
générique" (ex: "Data Analyst") n'était pas ce que le discours produit
laissait entendre ("un CV adapté à cette offre précise"). Corrigé en
ajoutant `POST /onboarding/roles/from-posting`, qui adapte contre le
**texte complet d'une offre** (titre + description collée par
l'utilisateur), pas juste un nom court. Repositionne aussi le produit
face à la critique "qui paierait pour ça" (voir PRODUCT.md) : ceci marche
pour n'importe quel métier, indépendamment de la liste d'entreprises
connues de `/discovery` — l'utilisateur colle une offre trouvée n'importe
où (LinkedIn, un ami, une affiche).

**Bug d'hallucination trouvé et corrigé en testant** : sur un vrai CV de
femme de ménage adapté à une vraie offre mentionnant "restocking
mini-bars", le bullet généré a fait fuiter "mini-bar items" dans
l'expérience du CV alors que ce terme n'existait nulle part dans le CV
source — seulement dans le texte de l'offre. Exactement le type de faille
que toute l'architecture est censée empêcher, révélée seulement parce que
le texte cible peut désormais être long et détaillé (une offre entière)
au lieu d'un simple nom de rôle, donnant au LLM bien plus de vocabulaire
plausible à "fusionner" par erreur. Corrigé en resserrant le prompt de
`role_adaptation_service.py` (et son prototype associé, gardés
synchronisés) : règle explicite interdisant qu'un terme du texte de
l'offre se glisse dans un bullet sous prétexte de ressemblance avec une
tâche déjà présente dans le profil de base. **Revérifié après coup** :
même scénario exact, "mini-bar" absent du CV généré, et le système
explique maintenant honnêtement l'écart dans `coverage_notes` au lieu de
l'inventer.

**Deux autres bugs trouvés et corrigés dans la foulée** :
- `Content-Disposition` du téléchargement plantait en 500
  (`UnicodeEncodeError`) dès qu'un nom de rôle contenait un caractère hors
  Latin-1 (le tiret cadratin de "Titre — Entreprise", jamais vu avant car
  les noms de rôle génériques testés jusqu'ici étaient tous ASCII simple).
  Corrigé avec un secours ASCII + `filename*=UTF-8''` (RFC 6266).
- Coller deux fois la même offre (même titre + même entreprise) plantait
  en 500 (contrainte `UNIQUE(user_id, name)`). Corrigé : désambiguïsation
  automatique du nom (`"... (2)"`, `"... (3)"`...) au lieu de bloquer.

**Testé en réel à trois niveaux** (local, production API, production vrai
navigateur avec téléchargement réel) sur le scénario exact ci-dessus.

### Réinitialisation / suppression ciblée — bug critique évité (2026-08-15)

En construisant `DELETE /onboarding/profile` et `DELETE /onboarding/roles/{id}`
(demandés après qu'un testeur ait signalé que l'écran de relecture restait
figé sur d'anciennes données après suppression de tous ses CV), un bug
préexistant et plus grave a été trouvé par raisonnement, avant qu'un vrai
testeur ne le déclenche : `role_repository.replace_experiences` supprimait
puis recréait **toutes** les lignes `experiences` de l'utilisateur à chaque
`confirm_draft` — or `role_experience_bullets.experience_id` a
`ON DELETE CASCADE`. Résultat : reconfirmer son profil après avoir déjà créé
un rôle effaçait silencieusement les bullets de ce rôle (le rôle restait
visible, vidé de son contenu, aucune erreur).

Corrigé en le renommant `sync_experiences` : les expériences existantes
(clé = poste + entreprise) sont mises à jour sur place, jamais supprimées ;
seules les expériences réellement nouvelles sont insérées. **Vérifié en
réel** : rôle créé (2 bullets confirmés en base via `psql`), deuxième CV
uploadé, profil refusionné et reconfirmé (le scénario exact qui aurait
déclenché le bug) — 2 bullets toujours présents après coup, 2 nouvelles
expériences ajoutées en plus, rien perdu.

Les deux nouveaux endpoints ont ensuite été testés à trois niveaux : local
(`curl` + vérifications SQL directes des cascades et des fichiers
physiques), production (`curl` sur un compte jetable), puis via un vrai
navigateur headless (Playwright) contre l'URL de production réelle —
inscription → upload → fusion → confirmation → création de rôle →
suppression du rôle → réinitialisation du profil, captures d'écran à
l'appui.

### Format des conflits de fusion resserré (2026-08-15)

Le champ `field` d'un conflit (`app/services/cv_merge_service.py`, prompt
brique fusion) était du texte libre généré par le LLM — pas fiable pour
qu'une interface l'applique automatiquement. Trouvé en voulant construire
un bouton "appliquer ce candidat" côté frontend : un même champ composite
(`date_range`) pouvait être scindé en deux conflits distincts partageant
le même `field`, chacun avec un candidat contenant seulement un
**fragment** de la valeur (ex: "Aug 2022" au lieu de "Aug 2022 – Aug 2024").
Prompt resserré (et son prototype `prototypes/cv-merge/merge_profiles.py`,
gardé synchronisé) : `field` doit être un chemin JSON strict
(`contact.email`, `experiences[1].date_range`), un seul conflit par champ,
valeur complète pour chaque candidat. Vérifié avec un vrai appel LLM sur
un cas de conflit reproduit fidèlement (2 CV, email + dates contradictoires).

### Découverte automatique (2026-08-15)

- `GET /discovery/known-companies` — liste de départ vérifiée en réel
  (2026-08-15, `app/data/known_companies.py`, 36 entreprises) : label,
  type ATS et board token déjà remplis. Répond à une question de
  l'utilisateur en testant : "comment je sais si c'est Greenhouse ou
  Lever ? le plus souvent on ne connaît pas le nom des entreprises, on
  postule juste en fonction de son profil" -- choix conscient de ne
  **pas** deviner une couverture large non vérifiée : chaque entrée a été
  testée en direct contre l'API publique correspondante avant d'être
  écrite (curl réel, 200 + au moins un poste ouvert au moment du test).
  Non exhaustif par construction -- l'ajout manuel reste possible pour
  toute entreprise absente de la liste.
- `POST /discovery/sources` — ajoute une entreprise à surveiller (Greenhouse/Lever)
- `GET /discovery/sources` — liste, avec statut et résumé du dernier passage
- `POST /discovery/run` — cherche sur toutes les sources actives, matche contre les rôles confirmés, met en file (canal plateforme, jamais d'auto-envoi)
- `GET /discovery/candidacies` — liste les candidatures trouvées, avec le
  lien vers l'offre d'origine (`posting_url`, joint depuis `postings.url`)
- `PATCH /discovery/candidacies/{id}` — suivi manuel de statut (2026-08-15,
  demandé par l'utilisateur : "comment je sais ce que j'en ai fait ?").
  Aucune règle d'enchaînement imposée entre les 7 statuts (`queued` →
  `sent` → `viewed` → `contacted` → `interview_scheduled` →
  `offer_received`/`rejected`) -- l'utilisateur peut sauter directement à
  n'importe lequel, ça reste sa réalité à décrire, pas une machine à états
  qu'on lui impose. `sent_at` posé une seule fois, à la première bascule
  vers `sent` -- jamais réécrit ensuite (même principe que
  `cover_letter_text` figée au moment de l'envoi).

**Testé en réel** : Palantir (Lever) + Stripe (Greenhouse), 886 offres
examinées, 7 candidatures pertinentes mises en file (scores 3-4). Relance
immédiate → 0 nouvelle offre, dédoublonnage confirmé sur un vrai volume.
Suivi de statut testé en réel (2026-08-15) : bascule vers `sent`,
`sent_at` posé, rebascule vers `sent` → `sent_at` inchangé (vérifié) ;
tentative sur la candidature d'un autre utilisateur → 404, pas de fuite.

**Scope limité aux sources ATS** — Gmail (OAuth par utilisateur) et IMAP
(UI de saisie de mot de passe chiffré) restent CLI-only pour l'instant,
voir `PRODUCT.md`.

### Stockage persistant (2026-08-15)

En local : disque (`backend/storage/`, gitignored). En production : volume
Railway attaché au service, monté au même chemin — zéro changement de
code entre les deux. Testé en réel : fichier généré, redéploiement forcé,
fichier retéléchargé identique (voir `DEPLOY.md`). Limite assumée : un
volume ne scale pas à plusieurs instances — S3/R2 reste l'étape suivante
si le service tourne un jour en parallèle, sans changer la signature de
`core/storage.py` (`storage_key` reste une clé opaque).

### Suppression de compte admin (2026-08-15)

- `GET /admin/users` — liste tous les comptes, y compris ceux créés avant
  l'activation du filtre d'invitation (absents de `beta_invites`).
- `DELETE /admin/users/{email}` — supprime un compte : données en base
  (CASCADE), fichiers physiques uploadés/générés, et son invitation bêta
  (pas liée par FK, sinon l'email resterait marqué "déjà invité" pour
  toujours).

Ajouté pour nettoyer les comptes de test créés en production pendant les
sessions de test précédentes (pas de clé SSH pour le faire via `psql`).
**Testé en réel** : compte créé avec un vrai CV uploadé, supprimé, vérifié
en base (ligne `users` absente), sur disque (dossier vide) et
ré-invitable immédiatement après (pas de conflit "déjà invité"). Utilisé
ensuite pour nettoyer 8 comptes de test en production, dont 3 créés avant
le filtre d'invitation et retrouvés seulement grâce à `GET /admin/users` —
`ewilliantagain@gmail.com` (testeur réel) et le compte personnel de
l'opérateur n'ont jamais été touchés.

### Comptes email — première brique de l'auto-envoi (2026-08-16)

Porte vers le web la capacité "candidater pendant que je dors" (Phase 1
CLI, validée sur tensoratech.com) — décision tranchée avec l'utilisateur :
envoyer réellement depuis la boîte mail de l'utilisateur (SMTP, ses
propres identifiants), pas depuis un domaine partagé CV Autopilot. Plus
crédible pour le recruteur qui reçoit l'email, et ne dépend d'aucune
vérification de domaine côté fournisseur d'envoi (contrairement à Resend
utilisé en Phase 1, qui exige un domaine vérifié par expéditeur).

- `POST /email-accounts` — connecte un compte (label, host/port IMAP,
  host/port SMTP, username, password). **Vérifie la connexion IMAP avant
  d'enregistrer quoi que ce soit** — mot de passe/host invalide échoue
  immédiatement avec un message clair, rien n'est stocké en cas d'échec.
  Le mot de passe est chiffré (`core/crypto.py`, Fernet) avant écriture,
  jamais en clair en base, jamais renvoyé par l'API.
- `GET /email-accounts` — liste (jamais `encrypted_password` dans la réponse).
- `DELETE /email-accounts/{id}` — déconnecte un compte.

`app/adapters/imap_adapter.py` porté tel quel depuis `engine/adapters/`
(lecture seule, `readonly=True`). `app/adapters/smtp_adapter.py` (nouveau)
envoie via `smtplib`/SSL, avec `dry_run` par défaut partout où il est
appelé pour l'instant — même principe que Resend en Phase 1 CLI, jamais
d'envoi réel sans un geste explicite déjà vérifié.

**Testé en réel** : chemin d'erreur vérifié contre un vrai serveur IMAP
(`webmail.tensoratech.com`, déjà validé en Phase 1) avec un mot de passe
volontairement faux — connexion réellement tentée, rejet propre, 0 ligne
en base après l'échec (vérifié en SQL direct). Chiffrement vérifié en
isolation (round-trip encrypt/decrypt).

**Chemin de succès validé par l'utilisateur lui-même (2026-08-16)**,
directement dans l'interface en production, avec ses propres identifiants
(`ermanwilliantag@tensoratech.com`) — jamais partagés dans cette
conversation, exactement comme prévu. Compte connecté, toujours présent
après rechargement de la page (confirme une vraie persistance en base,
pas un affichage optimiste côté client).

Bug annexe trouvé par l'utilisateur juste après et corrigé : le libellé
et l'adresse email du compte s'affichaient collés sans espace (marge CSS
seule, aucun caractère espace réel dans le texte — invisible au
copier-coller ou à un lecteur d'écran). Même défaut trouvé et corrigé à
2 autres endroits de `/discovery` (type de source ATS, titre d'une
candidature).

**Prochaines étapes pour compléter le canal email** (pas encore
construites) : découverte par alertes (parser `email_alert_service.py`
de Phase 1, pas encore porté), génération de lettre de motivation (brique
absente du web aujourd'hui), endpoint d'envoi réel avec aperçu avant
confirmation.

### Bêta sur invitation (2026-08-15)

- `/auth/signup` refuse toute adresse absente de `beta_invites` tant que
  `BETA_INVITE_ONLY=true` (défaut). Passer à l'ouverture publique = mettre
  ce réglage à `false`, aucun changement de code.
- `POST /admin/beta-invites {"email": "..."}` — invite une adresse.
  Protégé par `Authorization: Bearer <ADMIN_TOKEN>`.
- `GET /admin/beta-invites` — liste les invitations.

Premier testeur invité en production : `ewilliantagain@gmail.com`.

## Ce qui n'existe pas encore

Candidatures : canal email (envoi direct), relances automatiques,
génération de la lettre de motivation associée. Paiement. Découverte
Gmail/IMAP côté web.
