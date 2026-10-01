# PROGRESSION PHASES — CV Autopilot
> Mémoire persistante de ce projet.
> À uploader dans Claude au début de chaque session.
> Claude lit ce fichier → reprend exactement où on s'est arrêtés.
> Mis à jour à la fin de chaque session — même 2 lignes suffisent.

---

## COMMENT UTILISER CE FICHIER

```
DÉBUT DE CHAQUE SESSION
→ Ouvrir Claude Project
→ Uploader ce fichier
→ Dire à Claude : "Lis PROGRESSION_PHASES.md et reprends où on s'est arrêtés"
→ Claude a tout le contexte immédiatement

FIN DE CHAQUE SESSION
→ Mettre à jour :
   - Statut des phases
   - Section "Dernière session"
   - Section "Prochaine session"
→ Sauvegarder
→ Tu peux partir 6 mois — rien n'est perdu
```

> **Note** : ce projet est piloté depuis Claude Code (CLI), pas depuis un
> Claude Project web — la mémoire persistante réelle du code/de la
> documentation vit dans `PRODUCT.md`, `backend/README.md` et
> `frontend/README.md` à la racine du projet (mis à jour à chaque
> fonctionnalité, avec le détail des tests réels). Ce fichier-ci sert de
> vue d'ensemble condensée pour reprendre le contexte stratégique
> rapidement, pas de journal technique ligne à ligne.

---

## IDENTITÉ DU PROJET

```
Nom du projet     : CV Autopilot
Date de démarrage : 2026-08-13
Dernière session  : 2026-08-16
Claude Project    : N/A — piloté via Claude Code (CLI), pas claude.ai/projects
Repo GitHub       : github.com/aiengineernlp-dotcom/systeme_de-gestion_de_projets
                    (monorepo personnel — code sous PRODUITS/01-cv-autopilot/)
Stack validée     : Backend FastAPI (Python) · Frontend Next.js 16 + Tailwind v4
                    · DB PostgreSQL (Railway) · LLM via OpenRouter · Hébergement
                    Railway (2 services : backend + frontend, déployés séparément)
                    · Email Resend (Phase 1 CLI) + SMTP propre à l'utilisateur
                    (Phase 2 web, en cours)
Objectif V1       : Automatiser la partie fastidieuse d'une candidature — un CV
                    honnêtement adapté à une offre précise en quelques secondes,
                    jamais un fait inventé — sans prétendre remplacer la
                    recherche d'emploi elle-même (LinkedIn/Indeed restent
                    imbattables en volume d'offres, ce n'est pas la bataille à
                    mener).
Deadline V1       : Non fixée — bêta privée déjà en ligne, ouverture publique
                    "à tout moment" une fois la mécanique jugée assez solide.
```

---

## CADRE PRODUIT — RAPPEL FONDAMENTAL (recadrage utilisateur, 2026-08-16)

> À lire en premier au début de chaque session, avant toute décision. Ce
> n'est pas nouveau (déjà présent dans `PRODUCT.md` § "Pourquoi ça existe"),
> mais l'utilisateur a senti un risque de dérive et a demandé à le graver
> ici pour ne plus jamais le reperdre de vue.

**Le vrai problème que ce produit résout : le temps que prend UNE seule
candidature**, pas "trouver un travail". En moyenne 15-20+ minutes par
offre — chercher le CV, l'adapter au format ATS, lire l'offre, adapter le
CV à cette offre précise, tout vérifier, chercher l'offre elle-même,
envoyer. Multiplié par plusieurs offres par jour, c'est ingérable en fin
de journée (voir le scénario "16h30" dans `PRODUCT.md`).

**CV Autopilot n'est PAS "une plateforme où les gens cherchent du
travail".** C'est **une plateforme qui facilite le fait de postuler à un
travail**. La nuance compte : on ne construit pas un moteur de recherche
d'emploi de plus (LinkedIn/Indeed sont déjà imbattables sur ce terrain).

**Précision du 2026-08-16 (ne pas mal interpréter la phrase précédente) :**
"trouver du travail" fait quand même partie du système — **parce qu'on a
déjà les offres**, capturées automatiquement (Greenhouse/Lever + alertes
email Indeed/LinkedIn). La découverte automatique n'est pas la finalité du
produit, mais c'est un pilier nécessaire du moyen : c'est ce qui fait que
**l'offre vient à l'utilisateur** au lieu que l'utilisateur doive aller la
chercher (et parfois s'inscrire sur une plateforme juste pour voir si un
poste lui correspond). Une fois l'offre capturée, l'utilisateur clique un
lien déjà prêt (ou la candidature est déjà partie) — c'est ça, la
facilitation. Découverte = moyen. Postulation sans friction = finalité.

**Idées ouvertes du 2026-08-16, pas encore tranchées :**
- Élargir les sources de découverte au-delà de Greenhouse/Lever/Indeed/
  LinkedIn : Google Jobs (agrégateur, affiche "posté il y a N jours",
  candidature parfois par WhatsApp/email selon l'offre) + plateformes
  d'emploi africaines ouvertes (parcourables sans inscription).
  Tension technique à résoudre avant de construire quoi que ce soit :
  Google n'a pas d'API publique gratuite pour ça — 3 voies possibles,
  pas équivalentes : (1) scraper la page de résultats Google Jobs
  directement → viole les CGU Google, même problème déjà écarté pour
  LinkedIn/Indeed ; (2) lire le balisage structuré `schema.org
  JobPosting` directement sur le site de l'employeur/job board (c'est la
  donnée source que Google lui-même indexe) → légitime, même logique que
  Greenhouse/Lever ; (3) service tiers payant (type SerpApi) qui proxy
  les résultats Google Jobs → pas de violation directe de notre côté,
  mais un coût récurrent à assumer.
- **Suivi après candidature** — l'utilisateur a soulevé que c'est "aussi
  le vrai problème", sans encore préciser quoi exactement (le CLI Phase 1
  a déjà `followup_service.py` — relance à J+7 — pas encore vérifié si
  porté côté web). À creuser en détail à la prochaine session avant de
  coder quoi que ce soit dessus.
- **"Le système doit prendre en compte tout type d'email"** — exigence
  explicite de l'utilisateur (2026-08-16), déclenchée par le blocage
  Gmail découvert le même jour : la majorité des utilisateurs auront un
  email personnel classique (Gmail/Yahoo/Hotmail), pas un domaine pro
  comme `tensoratech.com`. L'IMAP générique par mot de passe (déjà
  construit) ne couvre qu'une partie des cas :
  | Fournisseur | État | Ce qu'il faut probablement |
  |---|---|---|
  | Domaine perso/hébergé (Namecheap, cPanel, OVH...) | ✅ IMAP+mot de passe validé en réel | Déjà couvert |
  | Gmail | ❌ Bloqué (silencieux, découvert le 2026-08-16) | OAuth — porter `gmail_adapter.py` (CLI Phase 1) côté web avec un vrai flux de consentement par utilisateur |
  | Outlook/Hotmail/Live | ⚠️ Jamais testé | Microsoft a largement abandonné l'auth basique IMAP — probablement OAuth (Microsoft Graph) aussi, à vérifier en réel avant de supposer |
  | Yahoo, iCloud | ⚠️ Jamais testé | Historiquement encore ouverts à IMAP+mot de passe d'application — à valider en réel |

  → Conclusion : "tout type d'email" = au moins **deux mécaniques
  différentes** à construire (IMAP générique déjà fait + OAuth
  Gmail/Microsoft à porter), pas un simple ajustement de config. Vrai
  chantier, pas encore commencé. Le flux manuel ("colle une offre") ne
  dépend d'aucune connexion email — reste le filet de sécurité pour un
  utilisateur dont la boîte ne peut pas être connectée.

---

## ÉTAT GLOBAL

```
Phase actuelle    : Phase 2 — application web multi-utilisateur (bêta privée,
                    ewilliantagain@gmail.com + tensoratech@gmail.com invités)
Couche en cours   : Auto-envoi canal email ("candidater pendant que je dors") —
                    comptes email (IMAP+SMTP chiffrés) + découverte par
                    alertes email (Indeed/LinkedIn) construites, testées en
                    réel et poussées ; lettre de motivation + envoi réel
                    restent à construire
Statut global     : 🟡 En cours
Dernière mise à jour : 2026-08-16
```

**Repères historiques du projet** (ne correspond pas au découpage générique
Phase 1-4 du système Tensoratech — ce projet a son propre découpage, gardé
tel quel plutôt que forcé dans un moule qui ne correspond pas) :

```
Phase 1   ✅ Terminée — CLI, un seul utilisateur (Erman) : extraction,
             adaptation par rôle, mots-clés, génération .docx, envoi email
             réel (Resend), suivi dans tracker-candidatures.md
Phase 1.5 ✅ Terminée — découverte automatique d'offres (ATS Greenhouse/Lever
             + alertes email Indeed/LinkedIn), testée en réel sur volume
             (886 offres examinées, doublons éliminés)
Phase 2   🟡 En cours — port complet vers une app web multi-utilisateur
             (FastAPI + Next.js + Postgres, déployée sur Railway, bêta
             privée sur invitation)
```

---

## PROGRESSION DES DOCUMENTS — 00_ritual/

Ce projet n'a pas suivi le ritual de lancement en 11 documents du système
Tensoratech (antérieur à sa formalisation) — équivalences réelles :

| # | Document du ritual | Équivalent réel dans ce projet | Statut |
|---|----------|--------|-------|
| 1 | `Document_Maitre.md` | `PRODUCT.md` (racine du projet) | ✅ Vivant, mis à jour à chaque fonctionnalité |
| 2 | `Features_Complet.md` | Section checklist de `PRODUCT.md` | ✅ Vivant |
| 3 | `Syllabus_Mapping.md` | N/A — pas de composante formation | ⬜ Sans objet |
| 4 | `Cahier_de_charges.docx` | N/A — jamais formalisé, décidé au fil de l'eau avec l'utilisateur | ⬜ Sans objet |
| 5 | `Architecture_Projet.md` | `docs/DATA_MODEL.md` + `docs/schema.sql` + docstrings SoC dans chaque fichier | ✅ Vivant |
| 6 | `Marketing_Vente.md` | N'existe pas encore — page de présentation avant login pas construite | ⬜ À faire |
| 7 | `template_projet.md` | N/A | ⬜ Sans objet |
| 8 | `API_Spec.md` | Endpoints documentés directement dans `backend/README.md` | ✅ Vivant (pas un fichier séparé) |
| 9 | `Risk_Register.md` | Risques/limites connus documentés inline dans `PRODUCT.md` au fil des découvertes | ✅ Vivant (pas un fichier séparé) |
| 10 | `Test_Plan.md` | Pas de plan formel — chaque fonctionnalité testée en réel (comptes jetables, vrais appels LLM/API, vrai navigateur Playwright) avant d'être déclarée faite | 🟡 Pratique établie, jamais écrite comme plan à part |
| 11 | `Onboarding_Utilisateur.md` | `GUIDE_UTILISATION_PHASE1.md` (CLI uniquement) — rien d'équivalent pour le web | ⬜ Partiel |

---

## PROGRESSION DU BUILD — CE QUI EST RÉELLEMENT FAIT

### Phase 1 — CLI (un seul utilisateur) — ✅ Terminée et validée en réel
- Extraction de CV, fusion multi-CV, adaptation par rôle (17 rôles), mots-clés de matching, génération `.docx`, lettres de motivation par template
- Envoi email réel via Resend (dry-run puis `--send`), tracker de candidatures
- Découverte ATS (Greenhouse/Lever) + alertes email (Indeed/LinkedIn parsées depuis IMAP/Gmail)

### Phase 2 — Web multi-utilisateur — 🟡 En cours

**Fait et déployé (Railway, backend + frontend séparés) :**
- Auth (JWT), bêta sur invitation (`beta_invites`), isolation multi-utilisateur vérifiée en réel (deux comptes, tentatives croisées, aucune fuite)
- Onboarding complet : upload CV (.docx, tableaux inclus depuis le correctif du 2026-08-16) → fusion multi-CV avec détection de désaccords → résolution en un clic → confirmation → génération de CV
- **Pivot stratégique du 2026-08-16** : adaptation par **offre précise** (coller titre + description, pas juste un nom de rôle générique) — construit après avoir identifié l'écart entre la promesse produit et le code réel ; testé sur 3 profils très différents (tech, hôtellerie, vente/immobilier), un bug d'hallucination trouvé et corrigé au passage
- Découverte automatique (Greenhouse/Lever), liste de 36 entreprises connues vérifiées en réel, suivi de statut de candidature (7 états), lien direct vers l'offre
- Réinitialisation de profil / suppression de rôle ciblée, suppression de CV individuel
- Chiffrement des secrets (Fernet), administration bêta (liste/suppression de comptes)
- Comptes email (IMAP+SMTP, chiffrés) — connexion vérifiée avant enregistrement, testée en réel (chemin d'erreur confirmé contre un vrai serveur ; chemin de succès validé)
- **Découverte par alertes email (Indeed/LinkedIn) sur le web** (2026-08-16) — `email_alert_service.py` porté de la Phase 1 CLI, `discovery_service.run()` traite les sources `imap` en plus des sources ATS, nouvel endpoint `POST /discovery/sources/email-alerts`. Testé en réel via l'API HTTP complète (pas juste l'adapter) : compte `tensoratech.com` connecté, 251 offres trouvées, 206 nouvelles, 39 candidatures mises en file. Erreurs de sources isolées vérifiées séparément (compte supprimé → 404, IMAP injoignable → source passée en erreur sans bloquer les autres). Gmail testé aussi (`ermanwillian.canada@gmail.com`) : bloqué silencieusement par Google sur ce chemin IMAP par mot de passe — voir "Problèmes connus".
- **Lettre de motivation adaptée à l'offre précise** (2026-08-16) — `cover_letter_service.py`, pas un port du template statique CLI (`[PLACEHOLDERS]` par rôle) : génération LLM à partir des faits réels du rôle + du texte précis de l'offre liée à la candidature, même garde-fou anti-invention que `role_adaptation_service`. Nouvel endpoint `POST /discovery/candidacies/{id}/cover-letter`, régénérable tant que la candidature n'est pas envoyée. Testé en réel : 1er essai a fabriqué "I used Python for data cleaning" en combinant une compétence réelle avec une exigence précise de l'offre non établie par les faits — même bug déjà vu une fois côté adaptation de CV, prompt renforcé avec l'exemple concret correspondant, revérifié après correctif (respecte les faits, note même honnêtement un écart type Power BI non maîtrisé). Garde-fous 404/déjà-envoyée vérifiés séparément.
- **Envoi réel canal email** (2026-08-16) — `application_send_service.py`, assemble le dernier CV généré du rôle + la lettre déjà générée + les identifiants SMTP déchiffrés du compte email de l'utilisateur, délègue à `smtp_adapter.py` (existait déjà, jamais appelé jusqu'ici). Nouvel endpoint `POST /discovery/candidacies/{id}/send` : `confirm=false` (défaut) = aperçu exact sans connexion SMTP ni écriture DB, `confirm=true` = envoi réel qui fige la candidature (channel=email, status=sent, follow_up_due_at=J+7) en une seule transaction. Testé en réel de bout en bout (CV généré, compte tensoratech.com, lettre générée, aperçu, envoi réel confirmé par lecture IMAP du message reçu — bon sujet, bon corps, pièce jointe .docx 37060 octets). Bug trouvé à l'inspection du message brut : aucun header `Date`/`Message-ID` (dégrade le score anti-spam) — corrigé dans `smtp_adapter.py`, revérifié sur un second envoi réel.
- **Frontend branché sur les 3 briques ci-dessus** (2026-08-16) — connecter un compte email crée maintenant la source de découverte automatiquement ; chaque candidature non envoyée a un panneau "Rédiger la lettre & envoyer" (générer/régénérer la lettre, aperçu, confirmation d'envoi réel). **Vérifié par un vrai clic humain en navigateur** (pas seulement `tsc`/`build`) : connexion compte (1er essai échoué sur un mauvais mot de passe tapé -- validation a fonctionné comme prévu, 2e essai réussi), source auto-créée, lettre générée, envoi réel confirmé par lecture IMAP du message reçu, découverte lancée en vrai depuis l'UI (207 offres trouvées).
- **Candidature trackable depuis une offre collée, backend + frontend** (2026-08-16) — `candidacy_service.py`, nouvel endpoint `POST /discovery/candidacies/from-posting` : à partir d'un rôle déjà créé par `POST /onboarding/roles/from-posting`, crée le Posting+Application manquants (comblait l'écart trouvé en testant les 10 postes ci-dessous). Testé en réel : rôle → candidature → CV → lettre, sur une nouvelle offre. Isolation vérifiée (role_id d'un autre utilisateur → 404), doublon volontaire vérifié (coller deux fois la même offre crée deux candidatures distinctes, pas une erreur). Frontend branché le même jour : le bouton "Générer mon CV pour cette offre" (onboarding, Étape 3) crée maintenant aussi la candidature (échec silencieux si ça rate, jamais bloquant sur le CV), avec un lien "Suivre cette candidature →" sur la carte du rôle une fois créée.
- **Test sur 10 postes volontairement variés** (2026-08-16, `backend/scripts/personas/`) — 10 vrais comptes (signup réel), profils fast-forwardés à l'état confirmé (sans repayer l'extraction déjà validée), puis pour chaque poste : rôle depuis une offre précise (vrai LLM), CV, lettre, aperçu d'envoi -- tous réels. 10/10 passent de bout en bout. 9/10 lettres propres. 2 bugs de contamination offre→lettre trouvés et corrigés dans `cover_letter_service.py` : (1) persona immobilier -- la lettre inventait "actively working toward obtaining [a RERA license]", jamais dit ; (2) persona infirmière -- faits "general ward" redécrits "critically ill patients" en empruntant le niveau de gravité de l'offre (poste ICU). Les 10 comptes restent en base, réutilisables (voir README du dossier pour les identifiants).

**Pas encore fait (Phase 2) :**
- Pas de moyen de réactiver une source de découverte passée en erreur (ni endpoint ni UI) — limite pré-existante (pas propre aux alertes email), gênante : une panne IMAP passagère désactive la source pour toujours sans intervention manuelle en base
- Paiement (Stripe) — aucune tarification, aucune porte payante
- Page de présentation avant connexion (marketing/vente)
- Vérification OAuth Google (bloque Gmail multi-utilisateur au-delà de 100 comptes de test)
- Recherche par mots-clés à travers de nombreux employeurs (au-delà de Greenhouse/Lever) — chantier séparé, plus large, non commencé

**Gate de validation Phase 2 (pas encore toutes cochées) :**
```
✅ Demo end-to-end tourne (upload → CV adapté → téléchargement, vérifié en réel)
✅ Isolation multi-utilisateur vérifiée en réel
✅ Aucune fonctionnalité livrée sans test réel (comptes jetables, vrai LLM, vrai navigateur)
⬜ Paiement fonctionnel
⬜ Page de présentation publique
⬜ Validé par : Erman — en cours, bêta privée active
```

---

## JOURNAL DES SESSIONS (condensé — voir PRODUCT.md pour le détail complet)

---

### 2026-08-16 — Session — Pivot stratégique + auto-envoi email (en cours)

**Ce qu'on a fait :**
- Discussion franche sur la valeur commerciale du produit ("je ne vois pas qui paierait pour ça") → identifié que la découverte automatique ne sert que les profils tech/corporate (vérifié en réel : quasi aucun poste non-tech chez les entreprises Greenhouse/Lever connues) et que l'adaptation se faisait par catégorie de rôle générique, pas par offre précise comme le discours produit le laissait entendre
- Construit l'adaptation par offre précise (`POST /onboarding/roles/from-posting`), testée sur 3 profils non-tech réels
- Recherche de plateformes d'emploi Afrique francophone/MENA (via Manu) — vérifiée en réel, conclusion : pas d'intégration automatisée possible sans violer les CGU (`robots.txt` "search=yes" autorise l'indexation façon moteur de recherche, pas l'extraction structurée) ; le flux manuel "colle une offre" suffit pour ce marché
- Démarré le portage de l'auto-envoi email (canal email, Phase 1 CLI) vers le web — comptes email IMAP+SMTP chiffrés construits et déployés
- **Machine redémarrée en cours de session** — reprise du contexte via `git status`/état DB (pas de mémoire de conversation persistée) ; `SECRET_ENCRYPTION_KEY` avait disparu de `backend/.env` (exportée dans un shell perdu au redémarrage, jamais écrite dans le fichier) — régénérée
- Porté `email_alert_service.py` (parsing Indeed/LinkedIn) et branché les sources `imap` sur `discovery_service.run()` — testé en réel via l'API HTTP complète : tentative sur Gmail (`ermanwillian.canada@gmail.com`) bloquée silencieusement par Google malgré 2FA + mot de passe d'application + page de déblocage (page supprimée par Google), test réussi sur `tensoratech.com` à la place — 251 offres trouvées, 39 candidatures mises en file. Données de test nettoyées, 2 commits poussés sur `main`

**Ce qui tourne ✅ :**
- Adaptation par offre précise, bout en bout, en production
- Connexion de compte email (chemin d'erreur ET chemin de succès vérifiés en réel)
- Découverte par alertes email (Indeed/LinkedIn) — bout en bout, vérifiée en réel côté backend (pas encore branchée côté frontend)

**Ce qui bloque ❌ :**
- Aucun blocage technique côté backend — juste pas encore construit : lettre de motivation, envoi réel
- Frontend pas branché sur `POST /discovery/sources/email-alerts` (voir section Phase 2 ci-dessus)
- Gmail inutilisable sur le chemin IMAP par mot de passe depuis cet environnement (voir Problèmes connus) — pas un blocage pour les autres hébergeurs email

**Décisions prises :**
- Auto-envoi email : depuis la propre boîte SMTP de l'utilisateur, pas un domaine partagé (plus crédible pour le recruteur, pas de vérification de domaine tierce à gérer)
- Pas d'intégration automatisée sur les plateformes d'emploi régionales (Bayt, Wuzzuf, Emploi.ma, etc.) — CGU trop restrictives, le flux manuel suffit
- Gmail reste hors du chemin IMAP générique côté web (cohérent avec le choix déjà pris de le garder CLI-only via OAuth) — pas une regression, une confirmation

**Prochaine session — commencer par :**
0. **Toujours vérifier `railway status --json` avant d'affirmer qu'un push est en production** — pas de lien GitHub->Railway, voir DÉPENDANCES & ACCÈS. Envisager `railway service source connect` pour ne plus avoir à y penser.
1. Décider si un endpoint de réactivation de source en erreur vaut le coup maintenant ou peut attendre (touche aussi la source "SEO" cassée en prod, trouvée le 2026-08-16)
2. OAuth Gmail/Microsoft pour la connexion email ("tout type d'email", exigence du 2026-08-16 — voir section CADRE PRODUIT) — chantier à part entière, pas une config
3. Détailler "suivi après candidature" avec l'utilisateur (ouvert le 2026-08-16, jamais creusé) — `follow_up_due_at` est maintenant posé à J+7 à l'envoi, mais rien n'envoie encore la relance elle-même
4. Décision de tarification (crédits à l'usage vs abonnement) — mise en pause volontaire, à trancher avec l'utilisateur

---

### 2026-08-14 / 2026-08-15 — Sessions — Construction complète de la Phase 2 web

**Ce qu'on a fait :**
- Port complet des 4 briques d'onboarding (extraction, fusion, adaptation, mots-clés) vers FastAPI + Postgres
- Frontend Next.js complet (onboarding, discovery, auth), déploiement Railway (backend + frontend), stockage persistant (volume Railway)
- Bêta sur invitation, chiffrement des secrets, isolation vérifiée en réel
- Plusieurs bugs réels trouvés en testant en direct avec l'utilisateur (onboarding verrouillé après confirmation, cascade de suppression silencieuse sur les bullets de rôle, extraction .docx ignorant les tableaux) — tous corrigés et revérifiés

**Ce qui tourne ✅ :**
- Parcours complet upload → CV téléchargé, en production, vérifié par un vrai navigateur

**Décisions prises :**
- Stockage : volume Railway plutôt que S3/R2 pour la bêta (suffisant tant qu'une seule instance backend tourne)
- Découverte automatique limitée aux API publiques Greenhouse/Lever — jamais de scraping LinkedIn/Indeed

**Prochaine session :**
1. (Réalisé le 2026-08-16 — voir ci-dessus)

---

## DÉCISIONS TECHNIQUES PRISES

| Date | Décision | Raison | Impact |
|------|----------|--------|--------|
| 2026-08-13 | SoC strict (Router/Service/Repository/Model/Adapter) dès la Phase 1 CLI | Base saine avant tout portage web | Le port vers FastAPI a été mécanique, pas une réécriture |
| 2026-08-15 | Stockage fichiers : volume Railway, pas S3/R2 | Suffisant pour bêta privée, zéro changement de code futur pour migrer | Ne scale pas à plusieurs instances backend — connu et assumé |
| 2026-08-15 | Bêta sur invitation (`beta_invites` + flag) | "Prêt pour le public à tout moment" sans ouvrir maintenant | Bascule publique = un flag, pas une migration |
| 2026-08-15 | Jamais d'auto-envoi sur canal "plateforme" (ATS) | Une candidature soumise via formulaire web ne doit jamais partir sans validation humaine | Le canal email reste le seul auto-envoyable |
| 2026-08-16 | Adaptation de CV par offre précise, pas par catégorie de rôle générique | Écart trouvé entre la promesse produit et le code réel | Réoriente l'argument de vente central du produit |
| 2026-08-16 | Auto-envoi email depuis la boîte SMTP propre de l'utilisateur | Plus crédible pour le recruteur, pas de domaine partagé à faire vérifier | Plus de travail (adapter SMTP dédié) mais plus honnête |
| 2026-08-16 | Pas d'intégration automatisée sur les jobboards régionaux (Afrique/MENA) | CGU explicitement restrictives sur la majorité des plateformes trouvées | Le flux manuel "colle une offre" reste le seul chemin pour ce marché |
| 2026-08-16 | Découverte par alertes email : une source `imap` par compte email connecté, jamais Gmail sur ce chemin | Réutilise le même modèle `discovery_sources` que les sources ATS (mêmes Repository/Service) plutôt qu'un système parallèle ; Gmail reste OAuth-only (CLI), confirmé après un vrai blocage Google testé en réel | Une source cassée (IMAP injoignable, compte supprimé, clé de chiffrement changée) est isolée et n'interrompt jamais les autres sources du même run |

---

## PROBLÈMES CONNUS & SOLUTIONS

| Problème | Statut | Solution trouvée |
|----------|--------|-----------------|
| Extraction `.docx` ignorait tout texte dans un tableau (mise en page très commune des modèles de CV gratuits) | ✅ Résolu | Parcours paragraphes + tableaux dans l'ordre réel d'apparition (2026-08-16) |
| Cascade `ON DELETE CASCADE` effaçait silencieusement les bullets d'un rôle à chaque reconfirmation de profil | ✅ Résolu | `sync_experiences` (upsert par clé), plus jamais un delete-then-recreate |
| Fuite d'un détail de l'offre collée dans un bullet de CV généré (hallucination-adjacent) | ✅ Résolu | Règle explicite ajoutée au prompt d'adaptation contre la contamination offre→CV |
| Même contamination offre→texte généré, retrouvée dans la lettre de motivation (2026-08-16) : "Python" (fait réel) + "data cleaning" (exigence de l'offre) fusionnés en "I used Python for data cleaning" jamais dit par le candidat | ✅ Résolu | Exemple concret ajouté au prompt de `cover_letter_service` (même famille de garde-fou que l'adaptation de CV, prompt différent donc protection à dupliquer explicitement) |
| Email envoyé par `smtp_adapter.py` sans header `Date` ni `Message-ID` (2026-08-16, trouvé en inspectant un message réel reçu par IMAP) — dégrade le score anti-spam | ✅ Résolu | `email.utils.formatdate()` + `make_msgid()` ajoutés, revérifié sur un second envoi réel |
| Lettre de motivation générée pour un profil immobilier ("Sales & Administrative Support" réel vs offre "Real Estate Sales Consultant" exigeant licence RERA + vente indépendante) a inventé "I'm actively working toward obtaining [a RERA broker license]" -- une démarche jamais dite, vérifiable en entretien (2026-08-16, trouvé en testant 3 personas : moi/Data Analyst, IT Support, immobilier -- les 2 autres étaient propres) | ✅ Résolu | Règle 3 du prompt renforcée : interdit d'inventer une démarche en cours pour combler un écart, pas seulement la compétence -- contourner l'écart sans le nommer plutôt que fabriquer un engagement à le combler |
| Même famille de contamination offre→lettre, sur le NIVEAU DE GRAVITÉ cette fois (pas une compétence) : faits "20+ patients per shift on a general ward" redécrits "critically ill patients" en empruntant le vocabulaire de l'offre (poste en soins intensifs/ICU) (2026-08-16, trouvé en testant 10 personas, `backend/scripts/personas/` -- 9/10 propres) | ✅ Résolu | Règle 2 du prompt renforcée avec cet exemple précis, revérifié : reste au contexte réel ("general ward") |
| Travail poussé sur `main` (plusieurs sessions) jamais réellement mis en ligne -- pas de lien GitHub->Railway, chaque déploiement doit être déclenché à la main (2026-08-16, découvert en inspectant la prod réelle sur demande de l'utilisateur : aucune des briques du jour n'y était visible) | ✅ Résolu pour aujourd'hui | `railway up` lancé à la main sur les 2 services (backend + frontend), vérifié `RUNNING` + `/health` répond. Pas résolu structurellement -- toujours manuel à chaque session tant que le lien GitHub n'est pas configuré (`railway service source connect`) |
| Source "SEO" (Lever) en erreur en production : 404 sur `api.lever.co/v0/postings/SEO` -- board token invalide, préexistant, pas lié au travail du jour | 🟡 Connu, pas corrigé | Aucune UI pour corriger/supprimer une source en erreur (voir ligne "réactivation de source" ci-dessus) -- même limite |
| `Content-Disposition` plantait en 500 sur un nom de rôle contenant un caractère hors Latin-1 | ✅ Résolu | Secours ASCII + `filename*=UTF-8''` (RFC 6266) |
| Découverte automatique ne sert que les profils tech/corporate (Greenhouse/Lever) | 🟡 Connu, assumé | Le flux "colle une offre" (adaptation par offre précise) contourne le problème sans dépendre de la liste d'entreprises |
| Auto-envoi email — chemin de succès (vraie connexion IMAP/SMTP) non testé par l'IA | ✅ Résolu | Validé par l'utilisateur en production (2026-08-16), compte tensoratech.com connecté et persistant après rechargement |
| Libellé + adresse email affichés collés sur `/discovery` (marge CSS sans espace réel) | ✅ Résolu | Espace réel ajouté à 3 endroits (compte email, type de source, titre de candidature) |
| `SECRET_ENCRYPTION_KEY` absente de `backend/.env` après redémarrage machine (2026-08-16) — bloquait tout déchiffrement de mot de passe IMAP/SMTP | ✅ Résolu | Régénérée et écrite dans `.env` (jamais commis, `.gitignore`) ; aucune vraie donnée perdue, seuls des comptes de test factices étaient chiffrés avec l'ancienne clé |
| Gmail (`imap.gmail.com`) bloque silencieusement le `LOGIN` IMAP par mot de passe d'application (TCP+TLS OK, `NOOP` répond, `LOGIN` ne répond jamais) même avec 2FA active, IMAP activé, mot de passe régénéré | 🟡 Connu, assumé | Cohérent avec le choix déjà pris de garder Gmail CLI-only via OAuth ; la page de déblocage historique (`accounts.google.com/DisplayUnlockCaptcha`) n'existe plus côté Google. Chemin IMAP générique validé en réel sur un autre hébergeur (tensoratech.com) à la place — pas un bug du code |

---

## DÉPENDANCES & ACCÈS

```
APIs utilisées :
→ OpenRouter (LLM)         — clé dans backend/.env (OPENROUTER_API_KEY) — statut : actif
→ Greenhouse Boards API     — publique, pas de clé — statut : actif
→ Lever Postings API        — publique, pas de clé — statut : actif
→ Resend (email, Phase 1 CLI uniquement) — clé dans engine/.env — statut : actif

Services externes :
→ Railway (backend + frontend + Postgres) — compte : Erman — statut : actif, en production
  ⚠️ IMPORTANT (trouvé le 2026-08-16) : **PAS de déploiement automatique depuis GitHub**
  -- `git push` sur `main` ne déploie rien tout seul. Chaque déploiement est manuel via
  `railway up` (CLI, projets `cv-autopilot-backend` / `cv-autopilot-frontend`, 2 projets
  Railway séparés, service à préciser avec `-s backend`/`-s frontend`). Avant ce jour-là,
  plusieurs sessions avaient écrit "déployé" dans ce fichier en supposant un lien
  GitHub->Railway qui n'existe pas -- toujours vérifier `railway status --json` (champ
  `activeDeployments[].createdAt`) avant de dire qu'un push est allé en prod. URLs :
  backend `backend-production-77a54.up.railway.app`, frontend
  `frontend-production-1d0a4.up.railway.app`.
→ GitHub (repo monorepo)   — compte : aiengineernlp-dotcom — statut : actif

Variables d'environnement requises (backend) :
→ DATABASE_URL              = fourni automatiquement par Railway (Postgres)
→ JWT_SECRET                = signature des tokens d'auth
→ OPENROUTER_API_KEY        = appels LLM (4 briques d'onboarding + adaptation)
→ SECRET_ENCRYPTION_KEY     = chiffrement Fernet (secrets IMAP/SMTP)
→ ADMIN_TOKEN                = protège les routes /admin/*
→ CORS_ALLOW_ORIGINS         = URL du frontend déployé

Accès base de données :
→ Postgres (Railway)        — host interne Railway — statut : configuré, migrations Alembic
```

---

## CHECKLIST AVANT CHAQUE PHASE SUIVANTE

```
☑ Tous les fichiers de la phase précédente tournent sans erreur (vérifié en réel, pas supposé)
☑ Chaque fichier a une seule responsabilité (SoC respecté — Router/Service/Repository/Model/Adapter)
☑ Le fichier ne connaît que la couche directement en dessous
☑ Aucune dépendance non validée ajoutée
☑ PRODUCT.md + README (backend/frontend) mis à jour à chaque fonctionnalité
☐ Gate de validation signée formellement — pratiqué de fait (test réel systématique) mais jamais coché comme un document séparé
```

---

## CHECKLIST FIN DE VERSION (avant de geler) — pas encore atteinte

```
☐ Paiement fonctionnel (Stripe) — pas commencé
☐ Page de présentation publique — pas commencée
☑ Documentation à jour (PRODUCT.md + README à chaque fonctionnalité, systématique)
☑ Aucune TODO silencieuse — chaque limite connue est documentée explicitement, pas cachée
☑ Variables d'environnement documentées (voir ci-dessus)
☑ Dépendances listées (requirements.txt / package.json)
☑ README à jour
☐ Version gelée / taguée sur GitHub — commits réguliers, pas de tag de version formel
☐ Prêt pour testeurs externes au-delà du cercle actuel (2 comptes : Erman + 1 invité)
```

---

## RÈGLE D'OR
> Ce fichier est la mémoire persistante de ce projet.
> Claude oublie entre les sessions. Ce fichier, non.
> 3 lignes à la fin de chaque session suffisent.
> Ne jamais fermer une session sans mettre à jour
> "Prochaine session — commencer par".
