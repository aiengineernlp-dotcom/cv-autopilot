# Déploiement — Railway

> **Statut (2026-08-15) : déployé et validé en réel.** Backend et frontend
> tous les deux en ligne sur Railway, parcours complet (inscription →
> upload CV → fusion → confirmation → rôle → génération → téléchargement)
> vérifié par un vrai navigateur contre les vraies URL de production.
>
> - Backend : https://backend-production-77a54.up.railway.app
> - Frontend : https://frontend-production-1d0a4.up.railway.app
>
> Les étapes ci-dessous restent la référence pour comprendre ce qui a été
> fait, ou pour redéployer depuis zéro (nouveau projet, rotation de clés...).

## Pourquoi Railway

Déjà le choix documenté dans `TOOLS/MA_STACK_PERSONNELLE.md` et `PRODUCT.md`
("Stack") avant cette session — pas une nouvelle décision.

## Ce qui est prêt

- `backend/railway.json` — build Nixpacks (détecte Python via
  `requirements.txt` automatiquement), commande de démarrage qui applique
  les migrations puis lance le serveur (`alembic upgrade head && uvicorn ...`).
  Migrations idempotentes : rejouées à chaque déploiement sans risque.
- `frontend/railway.json` — build Nixpacks (détecte Next.js automatiquement).
- `backend/app/config.py` — normalise `DATABASE_URL` quel que soit le
  format fourni par l'hébergeur (`postgres://` ou `postgresql://` →
  `postgresql+asyncpg://` automatiquement, sans édition manuelle).

## Étapes (dans l'ordre)

### 1. Connexion (bloquant, action humaine)

```bash
railway login
```
Ouvre le navigateur, authentifie ton compte Railway (ou crée-en un si tu
n'en as pas). Une fois fait, je peux reprendre la main pour le reste via
la CLI, sans repasser par le navigateur.

### 2. Créer le projet et la base de données

```bash
cd "PRODUITS/01-cv-autopilot/backend"
railway init                    # crée un nouveau projet Railway
railway add --database postgres # provisionne Postgres, DATABASE_URL auto-injectée
```

### 3. Variables d'environnement du backend

```bash
railway variables --set "JWT_SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
railway variables --set "SECRET_ENCRYPTION_KEY=$(python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
railway variables --set "OPENROUTER_API_KEY=<ta clé, jamais celle de dev réutilisée sans réflexion>"
railway variables --set "OPENROUTER_MODEL=anthropic/claude-sonnet-4.5"
# CORS_ALLOW_ORIGINS mis à jour après l'étape 5 (une fois l'URL du frontend connue)
```

**Génère des clés neuves pour la prod** — ne jamais réutiliser
`JWT_SECRET_KEY`/`SECRET_ENCRYPTION_KEY` du `.env` de dev.

### 4. Déployer le backend

```bash
railway up
railway domain   # génère une URL publique, ex: cv-autopilot-backend.up.railway.app
```

Vérifie : `curl https://<url-backend>/health` → `{"status":"ok"}`

### 5. Déployer le frontend

```bash
cd "../frontend"
railway init
railway variables --set "NEXT_PUBLIC_API_URL=https://<url-backend-étape-4>"
railway up
railway domain   # URL publique du frontend
```

**Important** : `NEXT_PUBLIC_API_URL` doit être réglée *avant* `railway up`
— Next.js grave sa valeur dans le code au moment du build, pas au démarrage
(voir `frontend/node_modules/next/dist/docs/01-app/02-guides/environment-variables.md`,
vérifié en Phase 2 avant d'écrire le premier code frontend).

### 6. Boucler CORS

Reviens sur le service backend, ajoute l'URL réelle du frontend :

```bash
cd ../backend
railway variables --set 'CORS_ALLOW_ORIGINS=["https://<url-frontend-étape-5>"]'
railway up   # redéploie avec la nouvelle valeur
```

### 7. Vérifier en réel

Ouvre l'URL du frontend, inscris-toi, refais le parcours complet (upload →
génération de CV → découverte) — le même que celui déjà validé en local
par Playwright, mais maintenant en production.

## Deux vrais bugs trouvés en déployant, invisibles en local

**1. `docs/schema.sql` absent du contexte de build.** La migration
initiale pointait vers `../../../../docs/schema.sql` — correct en local
(tout le monorepo est sur disque), mais `railway up` lancé depuis
`backend/` n'upload que ce dossier. Résultat : `FileNotFoundError` au
démarrage, jamais vu avant parce que le test local ne peut pas révéler ce
genre de problème par construction. Corrigé en copiant le schéma dans
`backend/db_schema.sql` (même raisonnement que `cv_style.py` — un fichier
qui doit voyager avec le service qui en dépend, pas rester dans le
monorepo parent).

**2. Nixpacks choisissait Node 18, Next.js 16 exige Node ≥ 20.9.** Le
`package.json` généré par `create-next-app` n'a pas de champ `engines` par
défaut — Railway a donc pris sa version par défaut, trop ancienne. Corrigé
en ajoutant `"engines": {"node": ">=20.9.0"}`.

Les deux corrections sont commitées (`backend/db_schema.sql`,
`backend/alembic/versions/0001_initial_schema.py`, `frontend/package.json`).

## Après le déploiement

- **Corrigé (2026-08-15)** — le stockage fichier persiste maintenant à
  travers les redéploiements : volume Railway (`backend-volume`) attaché
  au service `backend`, monté à `/app/storage` (même chemin qu'en local,
  zéro changement de code). Testé en réel : CV généré → redéploiement
  forcé (`railway redeploy`) → même fichier retéléchargé, identique octet
  pour octet (`diff` confirmé). Avant ce correctif, un redéploiement aurait
  silencieusement effacé tous les CV uploadés et générés de tous les
  utilisateurs.

  **Limite assumée de cette approche** : un volume Railway est attaché à
  une seule instance — ne scale pas si le service tourne un jour sur
  plusieurs instances en parallèle. Suffisant pour une bêta privée à
  faible concurrence ; passer à S3/R2 avant de scaler horizontalement
  (`backend/app/core/storage.py` déjà pensé pour ce remplacement sans
  changer les appelants — `storage_key` reste une clé opaque).
- `data-erman/beta_testers.json` (Phase 1.5) suit déjà les testeurs Google
  OAuth — même logique à étendre ici pour gérer qui a accès à la bêta.
- **Données de test restées en production, à nettoyer manuellement** :
  `prod-smoke-test@cvautopilot.dev` et un compte `e2e-prod-*` créés pendant
  la validation de ce déploiement. Je n'ai pas de clé SSH enregistrée pour
  m'y connecter et les supprimer (`railway ssh keys add` d'abord) — dit
  explicitement plutôt que deviné comme "propre". Sans impact fonctionnel,
  juste deux comptes de test visibles si tu regardes la base directement.
