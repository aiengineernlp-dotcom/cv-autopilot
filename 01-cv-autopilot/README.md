# CV Autopilot — Phase 1

Script en ligne de commande : matche une offre au bon CV, prépare la lettre,
envoie (canal email) ou met en file de validation (canal plateforme), logue
dans le tracker, calcule et envoie les relances J+7. Génère aussi les CV
manquants.

- [`GUIDE_UTILISATION_PHASE1.md`](GUIDE_UTILISATION_PHASE1.md) — pour tester
  pas à pas, dans l'ordre (commence ici si tu découvres le projet)
- [`PRODUCT.md`](PRODUCT.md) — vision produit, roadmap, décisions

## Architecture (Separation of Concerns)

```
engine/
├── config.py                          # Config — localise le dossier d'un client
├── cv_style.py                        # Presentation — primitives Word, générique (aucun rôle connu)
├── repositories/                      # Seule couche autorisée à toucher un fichier donné
│   ├── roles_repository.py            #   ↳ roles.json
│   ├── cover_letter_repository.py     #   ↳ cover-letters.md (lecture/parsing seulement)
│   ├── tracker_repository.py          #   ↳ tracker-candidatures.md
│   ├── profile_repository.py          #   ↳ profile.json
│   ├── cv_content_repository.py       #   ↳ cv_content.json (textes des CV par rôle)
│   ├── queue_repository.py            #   ↳ queue/
│   ├── discovery_config_repository.py #   ↳ discovery_watchlist.json (entreprises à surveiller)
│   ├── seen_postings_repository.py    #   ↳ seen_postings.json (anti-doublon découverte)
│   └── email_accounts_repository.py   #   ↳ email_accounts.json (comptes Gmail interrogés)
├── adapters/                          # Un fichier par technologie externe
│   ├── resend_adapter.py              #   ↳ seul fichier qui connaît Resend
│   ├── greenhouse_adapter.py          #   ↳ API publique Greenhouse Job Board
│   ├── lever_adapter.py               #   ↳ API publique Lever
│   ├── gmail_adapter.py               #   ↳ API Gmail (OAuth lecture seule, multi-compte)
│   └── posting.py                     #   ↳ forme normalisée d'une offre (type partagé)
├── services/                          # Logique métier — orchestrent Repositories/Adapters
│   ├── matching_service.py            #   ↳ score offre → rôle (pur, sans I/O)
│   ├── letter_service.py              #   ↳ remplit les placeholders (pur, sans I/O)
│   ├── application_service.py         #   ↳ orchestre une candidature de bout en bout
│   ├── cv_generation_service.py       #   ↳ orchestre la génération d'un CV
│   ├── followup_service.py            #   ↳ orchestre les relances J+7 dues
│   ├── email_alert_service.py         #   ↳ parse le texte des alertes Indeed en Postings (pur, sans I/O)
│   └── discovery_service.py           #   ↳ trouve des offres (ATS publics ET alertes email), les prépare via application_service
└── cli.py                             # UI — parse les arguments, appelle les Services, affiche
```

Règle appliquée partout : un fichier = une seule responsabilité. Les Repositories
sont les seuls à lire/écrire un fichier donné ; les Services orchestrent mais ne
touchent jamais un fichier eux-mêmes ; l'Adapter isole Resend (le remplacer =
modifier un seul fichier) ; le CLI ne fait qu'afficher. Chaque fichier porte un
commentaire d'en-tête indiquant sa couche, ce qu'il fait, ce qu'il ne fait jamais.

## Installation

```bash
cd "PRODUITS/01-cv-autopilot"
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # puis colle ta clé RESEND_API_KEY dedans
```

## Voir les rôles configurés

```bash
python -m engine.cli list-roles --client data-erman
```

## Générer le CV manquant d'un rôle

```bash
python -m engine.cli generate-cv ml-ai-engineer --client data-erman
```

Ajoute le contenu du rôle dans `data-erman/cv_content.json` (donnée, propre au
client), puis lance la commande — le style est repris automatiquement de
`engine/cv_style.py` (générique, marche pour n'importe quel domaine, pas
seulement tech/IA). Un nouveau client dans un autre domaine aurait son propre
`data-<nom>/cv_content.json`, jamais mélangé à celui-ci.

## Postuler — canal email direct (le seul envoi 100% automatique)

Toujours tester en dry-run d'abord (comportement par défaut, rien n'est envoyé) :

```bash
python -m engine.cli apply \
  --client data-erman \
  --company "Acme Corp" \
  --title "Data Analyst" \
  --description-file offre.txt \
  --recruiter-email hr@acme.com \
  --recruiter-name "Jane Doe"
```

Une fois satisfait, ajoute `--send` pour un envoi réel via Resend. Si la lettre
contient encore des `[PLACEHOLDERS]` non résolus, l'envoi réel est automatiquement
bloqué et repasse en dry-run.

## Postuler — canal plateforme (LinkedIn, Indeed, formulaires "Easy Apply")

Jamais d'auto-clic sur une plateforme tierce — le CLI prépare tout dans
`data-erman/queue/<date>-<entreprise>/` et loggue `📝 À valider (plateforme)`.

```bash
python -m engine.cli apply \
  --client data-erman --company "Acme Corp" --title "Data Analyst" \
  --description-file offre.txt --channel platform
```

## Forcer un rôle précis

```bash
python -m engine.cli apply --role-id ml-ai-engineer ...
```

## Relances J+7

Repère dans `tracker-candidatures.md` les candidatures `📤 Envoyé` dont la date
de relance est atteinte, envoie le suivi (canal email uniquement — cohérent
avec la règle "jamais d'auto-envoi sur une plateforme"), et met à jour le
statut en `🔄 Relance envoyée`.

```bash
python -m engine.cli run-followups --client data-erman          # dry-run
python -m engine.cli run-followups --client data-erman --send   # envoi réel
```

Cette commande ne se déclenche pas toute seule (cron local optionnel, voir
`GUIDE_UTILISATION_PHASE1.md`) — l'exécution serveur indépendante de la
machine de l'utilisateur est un sujet Phase 2, pas Phase 1 (voir `PRODUCT.md`).

## Recherche d'offres (Phase 1.5)

Cherche des offres sur une liste ciblée d'entreprises (`data-erman/discovery_watchlist.json`),
via les API publiques Greenhouse/Lever — jamais LinkedIn/Indeed (CGU interdisent
le scraping/l'automatisation). Filtre les offres déjà vues, score chaque offre
restante, et prépare les meilleures (jamais d'auto-envoi — une offre découverte
se postule via le formulaire propre à l'entreprise) dans `queue/` via le même
`application_service` que `apply`.

```bash
python -m engine.cli run-discovery --client data-erman
```

Édite `data-erman/discovery_watchlist.json` pour ajouter tes propres cibles :
```json
{ "sources": [
  { "provider": "greenhouse", "board_token": "nom-entreprise", "company_display_name": "Nom Entreprise" }
]}
```
Le `board_token` se trouve dans l'URL du board carrière de l'entreprise
(`boards.greenhouse.io/<token>` ou `jobs.lever.co/<token>`).

### Deuxième source : alertes email Indeed (Gmail ou n'importe quel hébergeur)

Lit (toujours lecture seule) les alertes emploi Indeed déjà reçues par email,
en extrait chaque offre, même pipeline dédoublonnage/score/préparation que la
watchlist ATS. Deux transports, même parsing (`email_alert_service.py`) :
Gmail (OAuth) ou IMAP générique (tout hébergeur — testé en réel sur
`tensoratech.com` chez Namecheap). Setup complet : `GUIDE_UTILISATION_PHASE1.md`
sections 3ter et 3quater.

```bash
python -m engine.cli run-gmail-discovery --client data-erman   # comptes Gmail
python -m engine.cli run-imap-discovery --client data-erman    # tout autre hébergeur
```

Comptes interrogés : `data-erman/email_accounts.json` (Gmail),
`data-erman/imap_accounts.json` (IMAP — mot de passe dans `.env`, jamais
dans ce fichier).

## Limites connues

- Matching par mots-clés seulement (titre pondéré 3× plus que la description,
  vraie limite de mot depuis le 2026-08-14) — pas encore de matching
  sémantique. Un mot-clé répété plusieurs fois dans une description générique
  peut encore franchir le seuil ; le filet de sécurité reste la validation
  humaine avant tout envoi sur le canal plateforme.
- Découverte email limitée à Indeed — pas de parsing LinkedIn (aucune alerte
  trouvée sur les comptes testés, l'utilisateur doit les activer lui-même).
- `run-followups`, `run-discovery`, `run-gmail-discovery` et
  `run-imap-discovery` doivent être lancées manuellement (ou par un cron
  externe) — pas de déclenchement
  automatique intégré en Phase 1.
- Un seul client (`data-erman`) pour l'instant — un deuxième client se fait en
  dupliquant la structure de `data-erman/` sous un nouveau dossier `data-<nom>/`.
