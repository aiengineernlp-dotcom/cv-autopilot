# Guide d'utilisation — Phase 1 (ligne de commande)

> Pour qui : toute personne qui veut tester CV Autopilot aujourd'hui, en l'état.
> Rien à cliquer — tout se passe dans un terminal. La Phase 2 (interface web,
> cliquable) aura son propre guide, différent de celui-ci.

---

## 1. Installer (une seule fois)

```bash
cd "PRODUITS/01-cv-autopilot"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Ouvre `.env` et remplis :
```
RESEND_API_KEY=re_...        # généré sur resend.com, domaine vérifié
FROM_EMAIL=ermanwilliantag@tensoratech.com
```

Sans clé Resend valide, tout fonctionne quand même — en **dry-run** (aperçu,
rien n'est envoyé). C'est même le mode recommandé pour tester sans risque.

**Chaque fois que tu ouvres un nouveau terminal**, réactive l'environnement :
```bash
cd "PRODUITS/01-cv-autopilot"
source .venv/bin/activate
```

---

## 2. Voir ce qui est déjà prêt

```bash
python -m engine.cli list-roles --client data-erman
```

Affiche les 17 rôles, leur CV associé, et d'éventuelles notes (ex : CV
manquant, contenu réutilisé d'un autre rôle). C'est le point de départ pour
savoir ce que le système sait déjà faire.

---

## 3. Postuler à une offre — le workflow du quotidien

### Étape 1 — Rassembler 3 infos sur l'offre
- Nom de l'entreprise
- Titre du poste
- Le texte de l'offre (colle-le dans un fichier, ex. `offre.txt`, ou passe-le
  directement en argument)
- L'email du recruteur si tu l'as (sinon, canal "plateforme" — voir plus bas)

### Étape 2 — Dry-run (toujours en premier)
```bash
python -m engine.cli apply \
  --client data-erman \
  --company "Acme Corp" \
  --title "Data Analyst" \
  --description-file offre.txt \
  --recruiter-email hr@acme.com \
  --recruiter-name "Jane Doe"
```
ou :
> python -m engine.cli apply --client data-erman --company "Acme Corp" --title "Data Analyst" --description-file offre.txt --recruiter-email hr@acme.com --recruiter-name "Jane Doe"

Le terminal affiche : le rôle détecté (et son score de correspondance), le CV
qui serait attaché, la lettre entièrement rédigée. **Rien n'est envoyé.**
Relis la lettre — c'est le moment de vérifier que ça sonne juste.

### Étape 3 — Envoi réel
Si l'aperçu te convient, relance la même commande avec `--send` :
```bash
python -m engine.cli apply \
  --client data-erman --company "Acme Corp" --title "Data Analyst" \
  --description-file offre.txt --recruiter-email hr@acme.com --send
```
ou 
> python -m engine.cli apply --client data-erman --company "Acme Corp" --title "Data Analyst" --description-file offre.txt --recruiter-email hr@acme.com --send

L'email part réellement, avec le CV en pièce jointe. Une ligne est ajoutée
dans `data-erman/tracker-candidatures.md` avec la date de relance (J+7).

### Cas particulier — offre trouvée sur une plateforme (LinkedIn, Indeed...)
Jamais d'envoi automatique sur une plateforme tierce (règle produit, pas juste
technique — voir `PRODUCT.md`). Utilise `--channel platform` :
```bash
python -m engine.cli apply \
  --client data-erman --company "Acme Corp" --title "Data Analyst" \
  --description-file offre.txt --channel platform
```
Le CLI dépose sujet + lettre + CV dans `data-erman/queue/<date>-Acme_Corp/`.
Tu ouvres ce dossier, tu copies-colles toi-même sur la plateforme.

### Si le mauvais rôle est détecté
```bash
python -m engine.cli apply --role-id ml-ai-engineer ...   # force le rôle
```

---

## 3bis. Laisser le système chercher les offres à ta place (Phase 1.5)

Au lieu de trouver l'offre toi-même, tu peux surveiller une liste
d'entreprises. Édite `data-erman/discovery_watchlist.json` :
```json
{ "sources": [
  { "provider": "greenhouse", "board_token": "stripe", "company_display_name": "Stripe" },
  { "provider": "lever", "board_token": "palantir", "company_display_name": "Palantir" }
]}
```
Le `board_token` se trouve dans l'URL du board carrière de l'entreprise
(`boards.greenhouse.io/<token>` ou `jobs.lever.co/<token>`) — cherche
"careers [nom entreprise]" pour la trouver.

```bash
python -m engine.cli run-discovery --client data-erman
```

Ce que ça fait : récupère les offres publiées par ces entreprises, ignore
celles déjà vues lors d'un passage précédent, garde celles qui matchent un de
tes rôles au-dessus d'un seuil, et les prépare dans `queue/` — **jamais
d'envoi automatique**, une offre découverte se postule toujours via le
formulaire propre à l'entreprise, donc toujours en validation humaine.

Seuil ajustable si trop/pas assez de résultats :
```bash
python -m engine.cli run-discovery --client data-erman --min-score 5
```

## 3ter. Découverte via tes alertes email Indeed (Gmail)

Si tu as des alertes emploi Indeed configurées sur une boîte Gmail, le
système peut les lire (lecture seule) et en extraire les offres — sans
jamais toucher Indeed/LinkedIn directement.

**Setup une fois** (voir aussi la section Google Cloud Console du guide) :
1. Crée un projet sur [console.cloud.google.com](https://console.cloud.google.com),
   active l'API Gmail, configure l'écran de consentement OAuth (scope
   `gmail.readonly` uniquement), crée des identifiants type "Desktop app",
   télécharge le JSON.
2. Place ce fichier dans `PRODUITS/01-cv-autopilot/` sous le nom
   `client_secret_gmail.json` (jamais commis — protégé par `.gitignore`).
3. Ajoute ton adresse Gmail dans `data-erman/email_accounts.json` :
   ```json
   { "accounts": ["ton.email@gmail.com"] }
   ```
4. **Important** : dans Google Cloud Console → OAuth consent screen → Test
   users, ajoute chaque compte Gmail que tu comptes connecter — sinon
   l'autorisation échoue avec `Error 403: access_denied`.

**Utilisation** :
```bash
python -m engine.cli run-gmail-discovery --client data-erman
```
La première fois pour un compte donné, un navigateur s'ouvre pour valider
l'autorisation (lecture seule). Ensuite, le jeton est réutilisé
automatiquement (`gmail_token_<compte>.json`, jamais commis non plus).

LinkedIn est supporté aussi (`jobalerts-noreply@linkedin.com`, même mécanique) —
il faut juste avoir des alertes emploi LinkedIn activées sur le compte
interrogé (aucune trouvée sur les comptes Gmail testés, mais 240 trouvées
sur un compte IMAP tiers — active les tiennes toi-même si besoin, LinkedIn →
Jobs → Alertes emploi).

## 3quater. Découverte via alertes email — n'importe quel hébergeur (IMAP)

Pas Gmail ? N'importe quelle boîte mail (hébergeur web, Zoho, Microsoft
365...) fonctionne via IMAP standard, en lecture seule.

**Setup une fois** :
1. Trouve les paramètres IMAP de ta boîte — souvent dans le panneau
   d'hébergement (cPanel) → Email Accounts → "Connect Devices". Tu as besoin
   du host, du port (généralement 993), et de ton adresse email complète.
2. Ajoute-les dans `data-erman/imap_accounts.json` :
   ```json
   { "accounts": [
     { "label": "monlabel", "host": "webmail.mondomaine.com", "port": 993, "username": "moi@mondomaine.com" }
   ]}
   ```
3. Mets le mot de passe **uniquement** dans `.env` (jamais dans ce fichier
   JSON, jamais dans le chat) :
   ```
   IMAP_PASSWORD_MONLABEL=le_mot_de_passe_de_la_boite_mail
   ```
   (le label doit correspondre, en majuscules, à celui du JSON)

**Utilisation** :
```bash
python -m engine.cli run-imap-discovery --client data-erman
```

**Dépannage — leçons d'un vrai test (tensoratech.com chez Namecheap)** :
- **Connexion qui ne répond jamais** : si ton domaine passe par Cloudflare,
  vérifie que l'enregistrement DNS du sous-domaine mail est en **"DNS only"**
  (nuage gris), pas "Proxied" (nuage orange) — Cloudflare ne relaie pas le
  trafic IMAP par défaut, la connexion reste bloquée indéfiniment sans ça.
- **`AUTHENTICATIONFAILED`** : réinitialise le mot de passe proprement depuis
  cPanel (Email Accounts → Manage → change password) plutôt que d'essayer de
  deviner un mot de passe existant.
- **Le vrai host n'est pas toujours `mail.tondomaine.com`** — vérifie via
  "Connect Devices" dans ton panneau d'hébergement ; chez certains hébergeurs
  c'est `webmail.tondomaine.com` ou un nom de serveur complètement différent.

---

## 4. Relancer les candidatures sans réponse (J+7)

```bash
python -m engine.cli run-followups --client data-erman          # aperçu
python -m engine.cli run-followups --client data-erman --send   # envoi réel
```

À lancer manuellement, ou en automatique via cron (voir section 6).

---

## 5. Générer le CV d'un nouveau rôle

Le contenu (résumé, expérience, projets, compétences) vit dans
`data-erman/cv_content.json` — c'est une donnée, pas du code. Ajoute une
entrée pour le rôle voulu (même structure que les entrées existantes), puis :

```bash
python -m engine.cli generate-cv <role-id> --client data-erman
```

Le style Word est repris automatiquement — rien à styliser à la main.

---

## 6. Rendre les relances vraiment automatiques (optionnel, cron local)

Ceci fait tourner `run-followups --send` une fois par jour, même sans toi —
tant que ton Mac est allumé (c'est la limite du cron local ; une vraie
exécution "même machine éteinte" est un sujet Phase 2, pas encore tranché).

```bash
crontab -e
```
Ajoute une ligne (exemple : tous les jours à 8h) :
```
0 8 * * * cd "/chemin/absolu/vers/PRODUITS/01-cv-autopilot" && .venv/bin/python -m engine.cli run-followups --client data-erman --send >> relances.log 2>&1
```
Remplace le chemin par le chemin absolu réel sur ta machine. Vérifie le
contenu de `relances.log` de temps en temps pour t'assurer que ça tourne.

---

## 7. Dépannage rapide

| Symptôme | Cause probable |
|---|---|
| `Rôle inconnu` | mauvais `--role-id`, vérifie avec `list-roles` |
| `Pas de CV généré pour...` | le rôle a `status: cv_manquant` dans `roles.json` — génère-le (section 5) ou utilise `--force` (déconseillé) |
| Envoi bloqué malgré `--send` | des `[PLACEHOLDERS]` restent non résolus dans la lettre — le message les liste |
| `RESEND_API_KEY manquant` | `.env` absent ou vide — voir section 1 |
| Email en spam | domaine pas (ou mal) vérifié sur Resend — voir `PRODUCT.md` |

---

*Phase 2 aura un guide séparé, pensé pour du clic, pas des commandes.*
