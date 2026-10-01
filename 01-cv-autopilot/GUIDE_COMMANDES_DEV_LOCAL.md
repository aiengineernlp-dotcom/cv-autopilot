# Commandes dev local — CV Autopilot

> Fiche pratique pour lancer/tester le projet en local sans redemander à
> chaque fois. Mis à jour le 2026-08-16. Toutes les commandes supposent que
> tu es dans `PRODUITS/01-cv-autopilot/` (racine du produit).

---

## Démarrage rapide (l'essentiel)

| Commande | Explication |
|---|---|
| `pg_isready` | Vérifie que Postgres tourne. Si erreur : `pg_ctl -D /opt/homebrew/var/postgresql@14 -l /tmp/postgres_log.txt start` |
| `cd backend && source .venv/bin/activate && alembic upgrade head` | Applique les migrations en attente (à faire après un `git pull` si le schéma a changé) |
| `cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8001` | Lance le backend FastAPI, rechargement auto à chaque modif de fichier `.py` |
| `cd frontend && npm run dev -- --port 3000` | Lance le frontend Next.js |
| `curl -s http://127.0.0.1:8001/health` | Vérifie que le backend répond (`{"status":"ok"}`) |

Une fois les deux lancés : **http://localhost:3000** pour l'app, **http://localhost:8001/docs** pour la doc interactive de l'API (Swagger, générée automatiquement par FastAPI).

---

## Arrêter les serveurs

| Commande | Explication |
|---|---|
| `pkill -f "uvicorn app.main:app"` | Arrête le backend |
| `pkill -f "next dev"` | Arrête le frontend |

---

## Base de données (Postgres local, `cv_autopilot_dev`)

| Commande | Explication |
|---|---|
| `psql -d cv_autopilot_dev` | Ouvre une session SQL interactive sur la base locale |
| `psql -d cv_autopilot_dev -c "select ... ;"` | Exécute une requête ponctuelle sans ouvrir de session interactive |
| `psql -d cv_autopilot_dev <<'SQL' ... SQL` | Exécute plusieurs requêtes d'un coup (heredoc) |
| `\d nom_table` (dans `psql`) | Affiche la structure d'une table |
| `createdb cv_autopilot_dev` | Crée la base si elle n'existe pas encore (première install) |

---

## Tester l'API sans navigateur (curl)

| Commande (forme générale) | Explication |
|---|---|
| `curl -s -X POST http://127.0.0.1:8001/auth/login -H "Content-Type: application/json" -d '{"email":"...","password":"..."}'` | Récupère un jeton (`access_token`) — indispensable pour tout appel authentifié ensuite |
| `... -H "Authorization: Bearer $TOKEN"` | Ajoute le jeton à n'importe quel appel protégé |
| `curl -s -o fichier.json -w "HTTP %{http_code}\n" ...` | Sépare le corps de la réponse (dans le fichier) du code HTTP (affiché) — évite les erreurs de parsing JSON quand on combine les deux |
| `python3 -m json.tool fichier.json` | Affiche un JSON de façon lisible |

---

## Vérifier un envoi email réel (lecture IMAP directe)

| Commande | Explication |
|---|---|
| `python3 -c "import imaplib; ..."` (voir historique de session) | Se connecte en lecture seule à une boîte IMAP et vérifie qu'un message est bien arrivé (sujet, expéditeur, pièce jointe) — la seule façon de vérifier qu'un envoi SMTP a *vraiment* été livré, pas juste que l'API n'a pas renvoyé d'erreur |

---

## Frontend : vérifier avant de committer

| Commande | Explication |
|---|---|
| `cd frontend && npx tsc --noEmit -p .` | Vérifie les types TypeScript sans générer de fichiers — rapide, à faire après toute modif de `.tsx`/`.ts` |
| `cd frontend && npm run build` | Build de production complet (Turbopack) — plus lent mais attrape plus d'erreurs que `tsc` seul |

---

## Git

| Commande | Explication |
|---|---|
| `git status` | Voit ce qui est modifié/non commité |
| `git add <fichiers>` | Prépare des fichiers précis pour le commit (éviter `git add .` — risque d'ajouter des fichiers hors sujet) |
| `git commit -m "..."` | Committe avec un message expliquant le *pourquoi*, pas juste le *quoi* |
| `git push` | Envoie les commits locaux vers GitHub (`origin/main`) |
| `git log --oneline -10` | Voit les 10 derniers commits, un par ligne |

---

## Reprendre une session Claude Code après un redémarrage

| Commande | Explication |
|---|---|
| `claude --continue` (ou `-c`) | Reprend automatiquement la toute dernière conversation, dans le même dossier |
| `claude --resume` (ou `-r`) | Affiche une liste des sessions passées pour ce projet, à choisir |

⚠️ Il faut être dans le même dossier (ou un parent) qu'au lancement initial, sinon l'historique n'est pas retrouvé.

---

## Notes importantes

- **`backend/.env`** contient les secrets (clé LLM, clé de chiffrement `SECRET_ENCRYPTION_KEY`...) — n'est jamais commité (`.gitignore`). S'il disparaît (ex: redémarrage machine, nouvelle installation), le déchiffrement des mots de passe IMAP/SMTP stockés casse silencieusement tant qu'il n'est pas régénéré.
- Toujours nettoyer les données de test créées en local (`DELETE` ciblé sur l'utilisateur de test) avant de committer — ne jamais laisser de données de test dans un commit.
