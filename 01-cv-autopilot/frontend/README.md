# Frontend — CV Autopilot (Phase 2)

Next.js 16 (App Router) + Tailwind v4. Consomme `../backend/` via son API
HTTP — aucune logique métier ici, uniquement affichage et appels réseau.

## Architecture

```
src/
  app/
    login/, signup/    Authentification
    onboarding/        Les 4 briques + génération de CV, tout sur une page
    layout.tsx          AuthProvider global
  lib/
    api.ts              Seul fichier qui parle au backend (fetch typé)
    auth.tsx             Contexte d'authentification (jeton JWT, localStorage)
  components/
    ui.tsx               Atomes visuels (Button, Card, StatusPill...)
    RequireAuth.tsx       Garde d'accès, redirige vers /login si déconnecté
```

Design repris tel quel de la maquette validée le 2026-08-14 (`PRODUCT.md`,
"Direction visuelle validée") : palette, typographies et tokens dans
`src/app/globals.css`, sans réinvention.

## Installer et lancer en local

```bash
cd frontend
npm install
cp .env.local.example .env.local  # NEXT_PUBLIC_API_URL -> backend local
npm run dev
```

Le backend (`../backend/`) doit tourner en parallèle (voir son README) et
autoriser l'origine `http://localhost:3000` en CORS (déjà configuré par
défaut, voir `backend/app/config.py` -> `cors_allow_origins`).

## Testé en réel (2026-08-15)

- `npm run build` : compile sans erreur, TypeScript inclus.
- Rendu serveur vérifié par requêtes HTTP réelles (`/login`, `/signup`,
  formulaires présents, statut 200).
- Le câblage vers le backend réutilise exactement les endpoints déjà
  testés en conditions réelles côté `backend/` (signup/login, upload,
  fusion, relecture, confirmation, création de rôle, génération et
  téléchargement de CV) — même contrat, mêmes types de réponse.

**Test interactif de bout en bout, complété (2026-08-15)** — Chromium
headless piloté par Playwright (installé en dev uniquement, pas une
dépendance du projet) : inscription → upload d'un vrai CV → fusion →
confirmation → création de rôle → génération → **téléchargement réel du
`.docx` via un clic de navigateur**, fichier récupéré et vérifié valide.
Même niveau d'exigence que `engine/`, `prototypes/` et `backend/` — pas
une exception silencieuse.

**Un bug trouvé en testant, mais dans le script de test, pas dans
l'application** : le premier passage échouait à l'étape "création de
rôle" — la syntaxe de sélecteur Playwright (`"text=cv_ready, text=draft"`
comme "OU") n'est pas valide dans ce framework. Vérification en base :
le rôle avait bel et bien été créé côté backend — l'application
fonctionnait, c'est le script d'assertion qui était mal écrit. Corrigé
(sélecteur basé sur la présence du bouton "Générer le CV"), rejoué avec
succès.

## Page `/discovery` (2026-08-15)

Ajouter une entreprise à surveiller (Greenhouse/Lever), lancer une
recherche, voir les candidatures trouvées — canal plateforme uniquement,
jamais d'auto-envoi. Lien depuis `/onboarding` une fois qu'au moins un
rôle existe.

**Testé en réel, parcours complet via un vrai navigateur** : inscription →
onboarding → ajout de Palantir → recherche (vrai appel à l'API Lever, 308
offres) → 2 candidatures affichées avec leur score. Réussi au premier
passage (contrairement au test précédent, aucun bug de script cette fois).

### Bug trouvé par l'utilisateur en testant lui-même (2026-08-15)

Une fois le profil confirmé une première fois, l'interface bloquait
**définitivement** l'ajout d'un nouveau CV et la refusion — `{!draftConfirmed}`
sur le bouton d'upload, `{!draft}` sur le bouton de fusion, tous deux
devenus des culs-de-sac dès qu'un draft confirmé existait. Trouvé en testant
avec un vrai compte (`ewilliantagain@gmail.com`) qui avait déjà un profil
confirmé d'un test précédent — invisible dans tous les tests E2E de cette
session parce qu'ils partaient toujours d'un compte neuf. Corrigé : le
bouton d'upload reste visible tant que le plafond de 3 CV n'est pas
atteint, et le bouton de fusion redevient "Mettre à jour mon profil"
après une première confirmation, au lieu de disparaître.

**Deuxième bug trouvé par l'utilisateur juste après, sur ce même
correctif** : le bouton "Mettre à jour mon profil" était bien visible,
mais grisé — impossible à cliquer. La correction d'affichage ci-dessus
n'avait pas touché `canMerge`, dont la propre condition
(`draft.status !== "confirmed"`) bloquait quand même l'action après
confirmation. Corrigé en simplifiant `canMerge` à la seule présence d'un
CV extrait.

**Retrait d'un CV uploadé** — bouton "✕" par ligne d'upload, appelle
`DELETE /onboarding/cv-uploads/{id}`. Écrit à part de la fonction `run()`
partagée : celle-ci renvoie `undefined` aussi bien en cas de succès (204,
pas de contenu) qu'en cas d'erreur, donc impossible de distinguer les deux
via sa valeur de retour pour une réponse vide — géré en `try/catch` direct.

**Troisième bug trouvé par l'utilisateur** : après avoir retiré tous ses
CV et rechargé la page, l'écran de relecture (Étape 2) et la liste des
rôles (Étape 3) restaient figés sur les anciennes données. Comportement
volontaire une fois expliqué — profil confirmé et rôles sont déjà
indépendants des uploads bruts, pour ne jamais abîmer une candidature déjà
envoyée — mais l'absence d'un moyen explicite de repartir à zéro était un
vrai manque. Deux boutons ajoutés sur recommandation, approuvés par
l'utilisateur ("Oui, vas-y") :
- **"Réinitialiser mon profil"** (Étape 1, visible dès qu'il y a un upload
  ou un draft) — vide CV uploadés + draft via `DELETE /onboarding/profile`,
  ne touche jamais aux rôles déjà créés. Confirmation via `window.confirm`
  avant l'appel.
- **"✕" par rôle** (Étape 3) — supprime un rôle précis et son `.docx`
  généré via `DELETE /onboarding/roles/{id}`. Confirmation via
  `window.confirm`, action définitive assumée (contrairement à la
  réinitialisation, qui ne touche jamais un rôle).

**Testé par un vrai navigateur headless (Playwright) contre l'URL de
production réelle**, pas juste en local : inscription → upload → fusion →
confirmation (bouton "Réinitialiser mon profil" apparaît, vérifié) →
création de rôle (bouton "✕" du rôle apparaît, vérifié) → suppression du
rôle (rôle disparaît de l'Étape 3, capture d'écran à l'appui) →
réinitialisation du profil (upload et draft disparaissent, l'Étape 3
disparaît entièrement puisque `draftConfirmed` redevient faux, capture
d'écran à l'appui). Script de test jetable (compte `ui-smoke-*@cvautopilot.dev`,
invité puis nettoyable), pas conservé dans le dépôt.

**Résolution de désaccord en un clic (2026-08-15)** — demandé par
l'utilisateur après avoir buté sur l'édition manuelle du JSON de relecture
pour corriger un email et une date contradictoires entre deux CV. Chaque
candidat d'un conflit est maintenant un bouton : le clic écrit sa valeur
au bon endroit dans le JSON (chemin résolu et vérifié avant écriture,
retombe sur l'édition manuelle si le chemin ne se résout pas), coche verte
sur le candidat actif. Nécessitait d'abord un prompt de fusion resserré
côté backend (voir `backend/README.md`) — sans ça, un `field` de conflit
mal formé aurait pu faire écraser la moitié d'un champ composite comme
`date_range`. Testé en réel : appel LLM direct, pipeline local complet,
puis un vrai navigateur contre la production — capture d'écran à l'appui,
confirmation réussie directement après un clic, sans repasser par la
fusion.

**Un seul bouton de confirmation, plus deux (2026-08-15)** — signalé par
l'utilisateur juste après : "je clique sur un désaccord mais c'est quoi
la suite ?" Avant, il fallait "Soumettre ma relecture" PUIS "Confirmer mon
profil", deux boutons sans lien visible entre eux, incohérent avec le
reste du parcours (upload → statut, création de rôle → rôle affiché — une
action, un résultat). "Confirmer mon profil" soumet maintenant toujours le
JSON courant avant de confirmer, en un seul clic. Ajouté un compteur de
progression ("X/2 désaccord(s) résolu(s)") sur le panneau de désaccords et
un rappel textuel tant qu'il en reste, pour que l'effet d'un clic sur un
candidat soit visible immédiatement, pas seulement déductible de la coche.
Testé en réel (état de désaccords forcé à zéro pour vérifier la
progression 0→1→2 de façon déterministe, un tirage LLM pouvant sinon
pré-remplir un champ par coïncidence) en local puis contre la production.

**Bouton de confirmation rapproché des désaccords (2026-08-15)** — testé
par l'utilisateur juste après le point ci-dessus : le bouton "Confirmer
mon profil" existait déjà et fonctionnait, mais restait après le pavé JSON
complet (16 lignes visibles) — invisible sans scroller une fois les
désaccords résolus, donnant l'impression qu'il manquait une étape.
Dupliqué : le même bouton (même handler `onConfirm`) apparaît maintenant
juste sous la liste des désaccords, en plus de celui en bas de la
relecture JSON complète — les deux font exactement la même chose, l'un
pour "je viens de résoudre mes désaccords, je valide tout de suite", l'un
pour "j'ai relu tout le JSON, je valide". Testé en réel (2 boutons
identiques détectés, clic sur celui du haut confirme correctement) en
local puis en production.

### Affichage d'une source en erreur corrigé (2026-08-15)

Signalé par l'utilisateur : une source Lever avec un `board_token` invalide
("SEO", pas une vraie entreprise sur Lever) passait bien en statut `error`,
mais la ligne "dernier passage" affichait des nombres vides au lieu d'un
message utile -- `discovery_service.run` écrit `{"error": str(e)}` dans
`last_run_summary` sur échec, forme différente de `{found, new, queued}`
sur un passage réussi, et le frontend lisait `.found`/`.queued` à l'aveugle
sur les deux formes. Corrigé : les deux formes sont distinguées
explicitement (`"error" in s.last_run_summary`), le message d'erreur réel
s'affiche en rouge.

Au passage, clarifié un comportement correct mais confus à l'affichage :
"0 mise(s) en file" sur une source déjà passée plusieurs fois signifie 0
**nouvelle** candidature à ce passage (tout était déjà connu, dédupliqué
via la contrainte `UNIQUE(user_id, source, external_id)`), pas 0 au total
-- la liste des candidatures plus bas reste cumulative sur tous les
passages. Ajouté le compte de "nouvelle(s)" à côté de "examinée(s)" et
"mise(s) en file", plus une mention "(toutes déjà vues avant)" quand
`new === 0`.

Testé en réel : source Lever invalide reproduite (404 confirmé côté API
Lever), message d'erreur vérifié affiché correctement en local puis en
production (vrai navigateur, token injecté pour un compte déjà préparé
via l'API).

### Lien vers l'offre + suivi de statut (2026-08-15)

Signalé par l'utilisateur en testant : une candidature "queued" n'avait
ni lien cliquable vers l'offre réelle (le texte de la page promettait
"à valider toi-même sur le lien d'origine", mais rien n'était cliquable),
ni moyen de dire "j'ai postulé" -- elle restait affichée `queued` pour
toujours, que l'utilisateur ait agi ou non.

Ajouté sur chaque ligne de "Candidatures trouvées" :
- **"Voir l'offre ↗"** -- lien direct vers `posting_url` (nouvel onglet),
  joint depuis `postings.url` côté backend puisque l'URL ne vivait que
  dans une chaîne `notes` non affichée.
- **Un menu déroulant de statut** à la place du badge figé (`queued`,
  `sent`, `viewed`, `contacted`, `interview_scheduled`, `offer_received`,
  `rejected`) -- change immédiatement, persiste en base (`PATCH
  /discovery/candidacies/{id}`), vérifié après rechargement de page.

Testé en réel en local puis en production (vrai navigateur) : lien
"Voir l'offre" présent et pointant vers une vraie URL Stripe, bascule de
statut confirmée persistante après reload, sur un compte avec de vraies
candidatures découvertes (32 en production).

### Ajout d'entreprise par nom, sans connaître Greenhouse/Lever (2026-08-15)

Signalé par l'utilisateur : "comment il va savoir que c'est Greenhouse ou
Lever ? le plus souvent on ne connaît pas le nom des entreprises, on
postule juste en fonction de son CV." Avant, le seul moyen d'ajouter une
source était de connaître le type ATS et le "board token" technique --
une vraie barrière pour un utilisateur qui ne vise pas des entreprises
précises.

Ajouté : un champ de recherche par nom au-dessus du formulaire (devenu
secondaire, replié derrière "Je connais déjà le board token"). Taper un
nom affiche les entreprises correspondantes dans une liste de départ
vérifiée côté backend (`GET /discovery/known-companies`) -- un clic
ajoute la source, type et board token déjà remplis. Les entreprises déjà
ajoutées disparaissent des suggestions ("Déjà dans tes sources
surveillées", distinct du cas "absente de la liste" qui renvoie vers
l'ajout manuel).

**Reste un vrai problème de fond, pas résolu par ceci** : cette liste
répond à "comment ajouter Stripe sans connaître son ATS", pas à "je ne
sais pas quelles entreprises viser du tout" -- ce deuxième point
demanderait une recherche par mots-clés/poste à travers de nombreux
employeurs (API de recherche d'emploi type Adzuna), pas encore construit,
chantier séparé et plus large (décision utilisateur du 2026-08-15 : les
deux dans cet ordre).

Testé en réel en local puis en production (vrai navigateur) : recherche
"Anthropic" → suggestion cliquable → source ajoutée avec le bon type
(`ats_greenhouse`) sans jamais l'afficher à l'utilisateur ; "Palantir" →
ajoutée en `ats_lever`, même principe.

### Étape 3 reformulée — "Colle une offre, obtiens ton CV" (2026-08-15)

Suite directe d'une conversation stratégique avec l'utilisateur ("je ne
vois pas qui paierait pour ça") : l'ancienne Étape 3 ("crée un rôle
générique par nom") ne délivrait pas ce que le discours produit
promettait. Devenue option secondaire, repliée derrière "Ou crée un CV
générique par type de poste" -- l'option principale est maintenant un
formulaire (titre, entreprise optionnelle, description complète collée)
qui appelle `POST /onboarding/roles/from-posting` **et** déclenche la
génération du `.docx` dans la même action (pas deux clics) -- le
téléchargement est prêt dès que la réponse revient.

Testé en réel sur un profil **non-tech délibérément choisi** (CV de femme
de ménage, une vraie offre d'hôtellerie à Abu Dhabi collée telle quelle)
pour vérifier honnêtement la promesse "marche pour n'importe quel métier"
après la critique du biais tech de `/discovery` -- pipeline complet en
local puis en production, vrai navigateur, téléchargement réel du
`.docx`, contenu relu et confirmé sans aucune invention (voir
`backend/README.md` pour le bug d'hallucination trouvé et corrigé au
passage).

### Section "Ton compte email" (2026-08-16)

Première brique de l'auto-envoi canal email (point 2 de la conversation
stratégique avec l'utilisateur, "candidater pendant que je dors").
Nouvelle section sur `/discovery`, au-dessus de "Sources" : connecter un
compte email (IMAP + SMTP, propre boîte de l'utilisateur), avec message
d'erreur clair si la connexion échoue (testé en réel contre
`webmail.tensoratech.com` avec un mot de passe volontairement faux).
Formulaire replié par défaut, comme les autres options avancées de cette
page (board token manuel, etc.).

## Ce qui n'existe pas encore

Détection/affichage des erreurs réseau génériques (offline, timeout),
édition champ par champ du profil en relecture (aujourd'hui : un textarea
JSON brut, fonctionnel mais moins soigné que la maquette d'origine — à
raffiner), dashboard de suivi des candidatures au-delà de la liste brute
de `/discovery` (statuts, relances), sources Gmail/IMAP dans l'écran de
découverte, design responsive mobile non vérifié.
