# CV Autopilot

> Système qui repère les offres pertinentes, matche le bon CV parmi plusieurs profils
> (SEO, Data Analyst, Data Engineer, Data Scientist, ML Engineer, NLP Engineer, AI Engineer...),
> rédige la lettre, envoie, log et relance — pour que l'utilisateur n'ait plus à chercher
> et cliquer manuellement sur chaque site.

---

## Pourquoi ça existe

Construit d'abord pour un besoin personnel réel : trop de CV différents (un par spécialité),
trop de sites à surveiller, trop de temps perdu à envoyer/relancer manuellement — du temps
qui devrait aller à se préparer aux entretiens ou monter en compétence, pas à remplir des
formulaires.

En le construisant bien dès le départ, il devient un produit vendable à toute personne dans
la même situation : plusieurs profils/CV, plusieurs pistes, pas le temps ou l'envie de tout
faire à la main.

**Le scénario qui résume tout** (utilisateur, 2026-08-14) : fini de travailler à 16h30, trajet
du retour, arrivée à la maison entre 21h et 23h. À ce moment-là, envoyer 10 CV demande au
minimum 15 minutes chacun — chercher, adapter, envoyer. Sans énergie, la candidature ne part
tout simplement pas. Ce n'est pas un problème de motivation, c'est un problème de temps et
d'épuisement en fin de journée. La promesse du produit : **soit c'est déjà validé et envoyé,
soit le lien est prêt et il ne reste qu'à cliquer** — plus jamais 15 minutes de recherche par
candidature.

---

## Vision — étoile du nord (le système final)

> Fixé le 2026-08-14, à partir d'une discussion approfondie avec l'utilisateur.
> Sert de référence pour trancher toute décision future : "est-ce que ça nous
> rapproche de ça ?"

### Ce que vit l'utilisateur final (quelqu'un qui n'a jamais codé)

**Inscription (10 minutes, une seule fois)** — Il arrive sur un site soigné, pas
un formulaire brut. Il paie (Stripe). On lui demande de coller son CV existant
ou de répondre à quelques questions ; une IA structure automatiquement son
profil et ses "casquettes" possibles, génère un premier jeu de CV adaptés par
rôle. **Il relit et valide** avant que quoi que ce soit ne devienne actif —
jamais un mot inventé qu'il n'aurait pas validé lui-même. Il règle ses
préférences : pays visés, salaire minimum, entreprises à exclure, volume
maximum de candidatures par jour.

**Ensuite — il ne fait plus rien.** Le système tourne sur un serveur, pas sur
sa machine : peu importe qu'il dorme, que son PC soit éteint. En continu, il
trouve des offres pertinentes, choisit/adapte le bon CV et la lettre, envoie
directement si un email existe, prépare et notifie pour validation si c'est
une plateforme, relance à J+7, ne postule jamais deux fois à la même offre, ne
dépasse jamais la limite quotidienne fixée. L'utilisateur reçoit une
notification de temps en temps, regarde son tableau de bord s'il en a envie,
et va en entretien quand ça sonne.

### Ce qui ne change jamais, peu importe le domaine de l'utilisateur

- **Email direct → automatique. Plateforme → jamais d'auto-clic, toujours
  validation humaine.** Non négociable, même à grande échelle.
- **Rien n'est envoyé sans être vérifiable en entretien** — zéro invention,
  même logique qui a fait corriger la lettre #13 et le statut fondateur.
- **Chaque utilisateur est isolé** — même principe que `data-erman/` séparé
  de `engine/`, porté en base de données.
- **Des limites, toujours** — volume quotidien plafonné, anti-doublon — pour
  ne jamais devenir un outil de spam qui détruit sa propre réputation d'envoi.
- **Design soigné** — les gens paient pour une expérience agréable, pas
  seulement une fonction qui marche.

### Ce qui existe déjà et se réutilise tel quel

| Aujourd'hui (Phase 1, CLI) | Système final |
|---|---|
| `application_service.py`, `matching_service.py`, `followup_service.py`... | Les mêmes fichiers, inchangés — appelés par une API au lieu du terminal |
| L'utilisateur qui tape la commande | Un scheduler côté serveur qui déclenche tout seul, 24/7 |
| L'utilisateur qui trouve l'offre et copie le texte | Un Adapter qui lit les offres publiques (ATS type Greenhouse/Lever) + les alertes email de l'utilisateur |
| `data-erman/` en dossiers | La même structure, en base de données — une ligne par utilisateur, isolée |
| `cv_content.json` écrit à la main | Généré par IA à l'onboarding, à partir de ce que l'utilisateur fournit, validé par lui |
| `.env` avec la clé Resend de l'utilisateur unique | Chaque utilisateur connecté via l'appli, ses propres réglages |

Rien de ce qui est construit en Phase 1 n'est jetable — c'est la moitié du
travail du système final, déjà faite et testée en réel.

---

## État actuel (2026-08-14) — ce qui existe et fonctionne, capacité par capacité

> Phase 1 et Phase 1.5 sont terminées et validées en conditions réelles —
> pas en théorie. 7 commandes CLI, chacune testée avec de vraies données.
> Cette section répond à "qu'est-ce qui se passe quand je fais X".

**Génération de CV** — `generate-cv <rôle>`
Lit `cv_content.json` (texte par rôle) + `profile.json` (identité), construit
un `.docx` au style visuel identique pour les 17 rôles, l'enregistre au bon
endroit, marque le rôle "cv_disponible" dans `roles.json`.
→ Résultat : un CV de plus, cohérent avec les autres, prêt à servir.

**Candidature manuelle, canal email** — `apply --recruiter-email ... [--send]`
Le titre et la description de l'offre sont comparés aux mots-clés des 17
rôles (titre pondéré 3× plus que la description, vraie limite de mot — pas
de sous-chaîne). Le rôle au meilleur score fournit son CV et sa lettre ; les
`[PLACEHOLDERS]` sont remplis. Sans `--send` : aperçu seulement, rien ne
part. Avec `--send` ET aucun placeholder non résolu : Resend envoie
réellement l'email, CV en pièce jointe.
→ Résultat : email réellement envoyé (ou aperçu), ligne loguée dans le
tracker, date de relance calculée à J+7.

**Candidature manuelle, canal plateforme** — `apply --channel platform`
Même matching, même lettre — mais **jamais d'envoi automatique**. Tout est
déposé dans `queue/<date>-<entreprise>/` (sujet, lettre, CV).
→ Résultat : toi tu ouvres le lien, tu colles, tu postules toi-même.

**Relance automatique** — `run-followups [--send]`
Scanne le tracker pour les candidatures "Envoyé" dont la date de relance
(J+7) est atteinte, remplit le template de suivi, envoie réellement si
`--send`.
→ Résultat : relance partie, statut passé à "Relance envoyée" — jamais
renvoyée deux fois (le "Relance le" est vidé après envoi).

**Découverte ATS** — `run-discovery`
Interroge chacune des 19 entreprises de `discovery_watchlist.json` via son
API publique (Greenhouse ou Lever — jamais LinkedIn/Indeed scrapés
directement, CGU obligent), score chaque offre, prépare celles au-dessus du
seuil (toujours canal plateforme). Anti-doublon : une offre déjà vue n'est
jamais retraitée.
→ Résultat : des candidatures prêtes sans que tu aies cherché quoi que ce
soit toi-même — limité aux entreprises de la liste.

**Découverte par alertes email, Gmail** — `run-gmail-discovery`
Connexion lecture seule (OAuth, autorisé une fois) à chaque compte listé
dans `email_accounts.json`. Cherche les alertes Indeed ET LinkedIn, extrait
chaque offre du texte de l'email (deux formats différents, un parser
chacun), même score/anti-doublon/préparation que ci-dessus.
→ Résultat : capte des offres que tu ne savais même pas avoir reçues.
Limite actuelle : seuls les comptes ajoutés comme "testeurs" Google
peuvent s'authentifier (100 max, app pas encore vérifiée).

**Découverte par alertes email, IMAP** — `run-imap-discovery`
Identique, mais pour une boîte mail hébergée n'importe où (validé en réel
sur `tensoratech.com`/Namecheap) — pas besoin que ce soit Gmail. Mot de
passe dans `.env`, jamais dans un fichier suivi par git.
→ Résultat : même chose, pour n'importe quel hébergeur email.

**Voir les rôles** — `list-roles`
Affiche les 17 rôles, leur CV, leurs notes (ex : contenu réutilisé d'un
autre rôle, capstones pas encore publiés).
→ Résultat : vue d'ensemble, aucune modification.

**Ce qui ne se déclenche jamais tout seul, aujourd'hui** : les 7 commandes
se lancent à la main (ou via un cron local, documenté dans
`GUIDE_UTILISATION_PHASE1.md`). L'exécution serveur autonome, indépendante
de toute machine, est un sujet Phase 2 — voir plus bas.

---

## Cible

- Chercheurs d'emploi actifs, notamment ceux avec plusieurs spécialités/CV en parallèle
  (reconversion, profils pluridisciplinaires, freelances).
- Pas pour du "spray and pray" en masse — le produit reste sur du matching qualifié CV ↔ offre.

---

## Niveau d'autonomie (choix produit, pas juste technique)

- **Email direct (recruteur / adresse RH)** → envoi 100% automatique, log automatique,
  relance programmée à J+7. C'est le canal sûr : rien qui viole des CGU tierces.
- **Plateformes (LinkedIn, Indeed, formulaires "Easy Apply")** → jamais d'auto-clic. Le
  système prépare tout (CV choisi + lettre + réponses probables) et met en file de
  validation. L'humain clique "envoyer" en quelques secondes.
- Cette limite reste valable même en version vendue : automatiser l'email est un choix
  produit durable, automatiser les plateformes tierces est un risque de compte (le client)
  et de réputation (nous).

**Discussion externe synthétisée (2026-08-14)** — l'utilisateur a exploré
l'architecture avec ChatGPT avant de synthétiser ici. Verdict : la majorité
de ce qui a été décrit (profil maître partagé entre variantes de CV,
architecture à adaptateurs par plateforme, rôles ouverts à tout domaine dès
l'entrée) était déjà construit ou déjà tranché — voir `docs/schema.sql`
(`experiences`/`role_experience_bullets`), `engine/adapters/posting.py` +
`EMAIL_SOURCES`, et la décision "rôles par utilisateur" de la même journée.
Un point a été explicitement rejeté : l'idée d'un "mode autopilot" qui
soumettrait automatiquement les candidatures sur les plateformes tierces
au-delà d'un seuil de confiance. Ça contredit la limite ci-dessus, qui reste
permanente, pas provisoire — les outils concurrents cités (auto-apply sur
LinkedIn/Indeed) le font vraisemblablement en marge des CGU de ces
plateformes ; leur existence n'est pas un argument pour les imiter.

---

## Roadmap

### Phase 1 — Usage perso (MVP, non multi-tenant)
- [x] Script qui lit `data-erman/profile.json` + les CV existants
- [x] Matching offre → CV (par mots-clés, `roles.json`)
- [x] Génération lettre depuis `cover-letters.md`
- [x] Envoi email (Resend) pour candidatures par email direct — testé en réel le 2026-08-14, arrivée en boîte de réception, CV attaché
- [x] Log automatique dans `tracker-candidatures.md`
- [x] Relance J+7 — logique construite et testée (`engine.cli run-followups`) : repère les candidatures dues, envoie via Resend, met à jour le tracker.

**Phase 1 est complète.** Toute la logique métier (matching, lettre, envoi,
tracking, relance) est construite et validée en conditions réelles le
2026-08-14 (emails reçus en boîte de réception, CV attaché, relance testée,
anti-doublon vérifié). Un cron local (documenté dans `GUIDE_UTILISATION_PHASE1.md`)
peut automatiser `run-followups` *pour un usage perso*, mais ce n'est **pas**
la solution produit — voir note Phase 2 ci-dessous pour pourquoi.
- [x] File de validation pour candidatures "plateforme"

### Phase 1.5 — Recherche d'offres

- [x] Source 1 : ATS publics (Greenhouse, Lever) — API publiques faites pour
      être consultées par des outils externes, aucune violation de CGU
      (contrairement à LinkedIn/Indeed, toujours exclus). Testé en réel le
      2026-08-14 contre Stripe (Greenhouse) et Palantir (Lever).
- [x] `discovery_watchlist.json` — liste ciblée d'entreprises à surveiller
      par client (volontairement pas une recherche ouverte sur tout le web).
- [x] Anti-doublon (`seen_postings.json`) — une offre n'est jamais retraitée
      deux fois.
- [x] Toujours `channel="platform"` — une offre découverte se postule via le
      formulaire propre à cette entreprise, jamais par email direct qu'on ne
      connaît pas ; donc jamais d'auto-envoi, toujours préparée pour
      validation humaine, même règle que pour LinkedIn/Indeed.
- [x] `engine.cli run-discovery` — testé en réel, 2 bugs trouvés et corrigés
      pendant ce test : collision de dossier `queue/` quand plusieurs offres
      de la même entreprise arrivent le même jour (corrigé : nom de dossier
      inclut le poste, `queue_repository` refuse maintenant tout écrasement
      silencieux), et faux positifs de matching sur du texte générique
      d'entreprise ("...les startups les plus ambitieuses...", pas le poste
      réel) — corrigé en pondérant le titre 3× plus que la description dans
      `matching_service`, mais **pas éliminé totalement** : un mot-clé répété
      plusieurs fois dans une description peut encore franchir le seuil. Le
      filet de sécurité reste la validation humaine avant tout envoi — pas un
      matching parfait, qui nécessiterait du matching sémantique (embeddings,
      voir Options futures).
- [x] 4e bug trouvé et corrigé (2026-08-14, pendant le test Source 2) : un
      mot-clé court ("geo") matchait comme simple sous-chaîne à l'intérieur
      d'un mot sans rapport — "**Geo**technical Design Engineer" matchait
      SEO/GEO Specialist. `matching_service` utilise maintenant une vraie
      limite de mot (`\b...\b`) au lieu d'un `.count()` naïf.
- [x] Source 2 : alertes email Indeed — construite et testée en réel le
      2026-08-14. `gmail_adapter.py` (OAuth lecture seule `gmail.readonly`,
      multi-compte — un jeton par compte) + `email_alert_service.py` (parse
      le texte brut des alertes en Postings). Résultat réel : découverte
      autonome d'un "Senior AI Engineer" pertinent depuis la boîte mail de
      l'utilisateur, sans jamais toucher LinkedIn/Indeed directement.
      3 bugs trouvés et corrigés pendant le test à grande échelle (~300
      offres) :
      1. `googleapiclient.discovery.build()` plantait (`UnknownApiNameOrVersion`)
         à cause de sa copie locale de la définition Gmail API — fix :
         `static_discovery=False`.
      2. Dédoublonnage intra-passage cassé : le set des offres "vues" n'était
         mis à jour qu'à la toute fin d'un passage, donc la même offre reçue
         dans deux emails du même jour n'était pas rattrapée pendant CE
         passage. Corrigé dans `discovery_service._evaluate_postings` — même
         bug touchait potentiellement la découverte ATS.
      3. L'URL Indeed change à chaque email même pour la même offre — le
         paramètre `jk` (job key) sert d'identifiant stable pour les offres
         organiques ; les annonces sponsorisées ("pagead") n'ont pas de `jk`,
         repli sur un hash (entreprise + titre) dans ce cas.
      - LinkedIn : voir plus bas, "Source LinkedIn ajoutée le 2026-08-14" —
        support ajouté après coup, trouvé en testant IMAP (0 alerte sur les
        comptes Gmail testés, 240 sur un compte IMAP tiers).
      - `email_accounts.json` (par client) liste les comptes Gmail interrogés.
- [x] Source 2bis : IMAP générique (n'importe quel hébergeur, pas seulement
      Gmail) — `imap_adapter.py`, testé en réel le 2026-08-14 sur
      `tensoratech.com` (hébergé chez Namecheap). Connexion + authentification
      réussies (0 email trouvé, normal — c'est une boîte pro, pas configurée
      pour recevoir des alertes Indeed, contrairement au Gmail personnel déjà
      validé). Diagnostic réel en cours de route, pas hypothétique :
      1. Le sous-domaine mail était "Proxied" sur Cloudflare (nuage orange) —
         Cloudflare ne relaie pas le trafic IMAP par défaut, la connexion
         restait bloquée indéfiniment. Fix : repasser en "DNS only".
      2. `imaplib.IMAP4_SSL` n'a pas de timeout par défaut — ajouté
         (`timeout=15`) pour avoir une vraie erreur plutôt qu'un blocage
         silencieux.
      3. Mot de passe à réinitialiser proprement depuis cPanel plutôt que
         deviné.
      - `imap_accounts_repository.py` + `imap_accounts.json` (config non
        secrète : host/port/utilisateur) ; mot de passe dans `.env`
        (`IMAP_PASSWORD_<LABEL>`, jamais commis).
      - `discovery_service.run_from_email()` renommé `run_from_gmail()` pour
        clarté (deux sources email désormais) ; nouveau `run_from_imap()` —
        les deux réutilisent le même `email_alert_service` (parsing) et le
        même `_evaluate_postings()` (dédup/score/préparation), seul le
        transport (Gmail API vs IMAP) diffère.
- [x] Source LinkedIn ajoutée le 2026-08-14 — `parse_linkedin_alert()`
      (`email_alert_service.py`). Trouvée en testant IMAP sur
      `tensoratech.com` : 240 alertes `jobalerts-noreply@linkedin.com` (0 sur
      les comptes Gmail testés). Format différent d'Indeed (séparateur par
      tirets, pas de description, ID stable dans le chemin de l'URL plutôt
      qu'un paramètre de requête) — `EMAIL_SOURCES` dans `discovery_service.py`
      fait tourner les deux parsers sur chaque compte (Gmail et IMAP),
      indifféremment. Résultat réel : 10 candidatures pertinentes générées
      (Data Scientist/AI Engineer chez Emirates, SEO Manager, ML Engineer...).
      Bug trouvé et corrigé pendant ce test : une section de pied de mail
      ("New jobs from your other alerts... see all jobs on LinkedIn: <url>")
      a été retenue par erreur — l'URL contenait "seo" comme paramètre de
      recherche (`?keywords=web+and+seo+python`), qui a matché SEO/GEO
      Specialist via la limite de mot. Corrigé en rejetant toute entrée dont
      un des 3 champs (titre/entreprise/lieu) contient une URL, ou dont le
      titre commence par des formules de pied de page connues ("See all
      jobs", "Edit alert", "New jobs from...").
- [x] Watchlist réelle constituée le 2026-08-14, volontairement multi-région
      (7 entreprises vérifiées : UAE — Cobblestone Energy, Palantir, AI71,
      Binance ; Afrique — One Acre Fund, Acumen, Welo Global). Correction
      importante suite à une remarque de l'utilisateur : la première
      recherche était centrée UAE/US par défaut, alors que le système doit
      fonctionner pour n'importe qui, n'importe où — le prompt de recherche
      (`PROMPT_RECHERCHE_ENTREPRISES.md`) est maintenant explicitement
      multi-région (Gulf, Afrique subsaharienne francophone et anglophone,
      France/Belgique). France/Belgique pas encore couvert par un bon
      candidat — à rechercher en priorité au prochain passage.
- [x] 3e bug trouvé et corrigé pendant le test à grande échelle (7 sources,
      ~900 offres) : le quota (`max_results`) comptait aussi les offres
      *rejetées*, donc une source bruyante (Welo Global, 577 offres) pouvait
      épuiser le quota avant même d'atteindre les autres sources — corrigé,
      le quota ne compte maintenant que les offres retenues. La sortie CLI a
      aussi été nettoyée (résumé groupé par entreprise pour les rejets, au
      lieu d'une ligne par rejet — sinon des centaines de lignes de bruit).
- Limite connue non corrigée : le champ "Pays" logué pour une offre
  découverte est un défaut fixe (`"UAE"`), pas la vraie localisation de
  l'offre (qui reste visible dans son URL/titre). Cosmétique, pas bloquant,
  mais à corriger avant Phase 2.

Un CV/lettre découvert automatiquement utilise le même pipeline que
`apply` (`application_service`) — aucune logique dupliquée, juste une
nouvelle façon d'alimenter les mêmes Services.

### Phase 2 — Multi-tenant / SaaS

**⚠️ Angle mort identifié (2026-08-14) — le vrai goulot d'étranglement,
à construire avant le reste.** Question de l'utilisateur : est-ce qu'on
tient vraiment la promesse "rendre la recherche d'emploi facile et
évidente", ou est-ce qu'on construit des pièces qui ne serviront pas ?
Réponse honnête : le squelette (schéma, canal email/plateforme, découverte
ATS/Gmail/IMAP, maquette onboarding) va dans la bonne direction, mais il
manque la pièce centrale — **"compréhension rapide du profil" n'existe pas
en code**. Pour Erman, ce travail a été fait à la main (conversations avec
Claude, contenu écrit manuellement dans `cv_content.json`) — pas
automatisé. Trois briques manquantes, à construire avant le backend/auth/
paiement, sinon Next.js/FastAPI/Stripe habillent une coquille vide pour
n'importe quel utilisateur autre qu'Erman :
1. **Extraction** — CV brut uploadé → profil structuré (postes, dates,
   compétences). Alimente `cv_uploads`/`extracted_profile_drafts`.
2. **Adaptation par rôle** — profil de base + rôle visé → bullets/summary
   différents à chaque variante (aujourd'hui : rédigé à la main par Claude,
   rôle par rôle, pour Erman).
3. **Génération des mots-clés de matching par rôle** — le matching
   (`matching_service.py`, déjà solide) compare une offre aux mots-clés
   d'un rôle ; pour Erman ces mots-clés viennent des échanges avec Claude,
   pour un inconnu il faut que le système les déduise seul.

**Brique 1 prototypée et testée (2026-08-14)** — `prototypes/cv-extraction/`,
sur le vrai CV Data Analyst d'Erman, en script isolé (pas branché au
produit). Résultat complet : `prototypes/cv-extraction/output/RESULTS.md`.
En résumé : fidélité à 100% sur tout ce qui est factuel et présent dans le
document (postes, dates, entreprises, diplôme, compétences) — aucune
invention détectée, données personnelles sensibles (nationalité, Emirates
ID) correctement isolées plutôt que réutilisées. Une limite réelle
découverte : `cv_content.json` contient un détail sur la certification
LogicMojo qui ne vient PAS du CV source (Erman l'avait donné en
conversation, pas par écrit) — l'extraction automatique ne peut pas le
deviner, et c'est heureux qu'elle n'ait pas essayé. Ça confirme concrètement
la nécessité du "champ libre optionnel" prévu à l'étape 2 de l'onboarding :
sans lui, tout ce qu'un utilisateur sait de lui-même mais n'a pas écrit sur
son CV reste invisible au système.

**Brique 2 prototypée et testée (2026-08-15)** — `prototypes/role-adaptation/`,
entrée = uniquement la sortie de la brique 1 (le profil Data Analyst),
rôle cible = "ML / AI Engineer" — comparé au `ml-ai-engineer` déjà validé
dans `cv_content.json`. Résultat complet :
`prototypes/role-adaptation/output/RESULTS.md`. En résumé : sur tout ce qui
est présent dans le profil de base, l'adaptation reformule et réordonne
fidèlement, avec la même sélection de faits que la version écrite à la
main. Deux écarts trouvés, tous deux du même type : le projet "Customer
Churn Prediction" et les compétences Deep Learning/NLP/LLM (PyTorch,
TensorFlow, Transformers...) de la version réelle n'existent nulle part
dans le CV "Data Analyst" utilisé comme seule source — **l'adaptation a
correctement refusé de les inventer plutôt que de les deviner**, et l'a
signalé explicitement (`coverage_notes`) au lieu de le cacher. Les deux
prototypes propagent la même honnêteté au lieu de compenser l'un pour
l'autre : ce que la brique 1 ne capture pas, la brique 2 ne l'invente pas
non plus.

**Décision tranchée (2026-08-15)** : upload jusqu'à 3 CV à l'onboarding
(minimum 1), possibilité d'en ajouter d'autres plus tard depuis le tableau
de bord sans bloquer la fin de l'onboarding. Chaque document est extrait
séparément par la brique 1 (inchangée, jamais concaténée à d'autres) puis
fusionné en **un seul** draft à relire — pas un écran de relecture par CV
uploadé, ça reproduirait la friction qu'on élimine. Les désaccords entre
documents (ex. deux numéros de téléphone différents) ne sont jamais
tranchés automatiquement : ils sont surfacés explicitement à l'écran de
relecture obligatoire. Détail complet et schéma mis à jour :
`docs/DATA_MODEL.md` (section correspondante) et `docs/schema.sql`
(`cv_upload_extractions`, `draft_source_uploads`, `extracted_profile_drafts.conflicts`).
**Logique de fusion prototypée et validée (2026-08-15)** — `prototypes/cv-merge/`,
vrai appel API, testée sur deux vrais CV d'Erman (Data Analyst et ML/AI
Engineer) qui décrivent les mêmes deux emplois et le même projet phare
(DataSphere360) avec des angles très différents — l'un présente un
framework de pipeline de données, l'autre le même projet comme un modèle
de prédiction de churn. **Le cas dur a été bien géré** : reconnu comme un
seul projet malgré le titre et l'angle différents, fusionné en une entrée
plus riche que chacun des deux documents pris isolément — exactement la
valeur recherchée par l'upload multi-CV. Un second projet présent
uniquement dans le second CV a été ajouté séparément, pas fusionné à tort.
Un désaccord a ensuite été injecté volontairement (téléphone différent,
statut de certification contradictoire) pour vérifier le chemin non couvert
par les deux vrais documents (qui ne se contredisaient sur rien) : les deux
désaccords ont été détectés et **le champ concerné est resté vide plutôt
que deviné** — le comportement le plus important tient. Les 4 briques du
pipeline d'onboarding (extraction, adaptation, mots-clés, fusion) sont
maintenant toutes prototypées et validées avec un vrai appel API. Détail :
`prototypes/cv-merge/output/RESULTS.md`.

**Brique 3 prototypée (2026-08-15), non marquée comme validée** —
`prototypes/matching-keywords/`, entrée = la sortie de la brique 2, sortie
= liste de mots-clés (équivalent du champ `keywords` de `roles.json`).
Résultat complet : `prototypes/matching-keywords/output/RESULTS.md`. Même
dynamique de propagation honnête que les deux briques précédentes : les
mots-clés Deep Learning/NLP/LLM absents du profil adapté (déjà signalés
comme non couverts par la brique 2) restent absents ici aussi, plutôt que
d'être régénérés à partir du seul nom du rôle. **Mais** — contrairement aux
briques 1 et 2 — le prompt de cette brique a été conçu après avoir regardé
la vraie liste de référence (`roles.json`), pas avant : la convergence
observée (mêmes 3 termes de titre, même choix d'exclure les noms
d'algorithmes trop granulaires) est donc partiellement informée par la
réponse attendue. **À retester à l'aveugle avec un vrai appel API avant de
faire confiance au résultat** — noté explicitement pour ne pas se
surestimer.

**Les trois briques rejouées avec un vrai appel API (2026-08-15,
OpenRouter)** — les trois scripts tournent maintenant pour de vrai
(`prototypes/_openrouter.py`, plus besoin de simuler le modèle à la main).
Brique 1 et 2 : résultats quasi identiques aux tests manuels, confirmant
que ce n'était pas un artefact de "Claude qui s'applique le prompt à
lui-même". **Brique 3 rejouée à l'aveugle sur un rôle jamais consulté dans
la session ("Data Engineer" plutôt que "ML / AI Engineer")** — cette fois
validée pour de vrai : 3 des 6 mots-clés réels manquent (`data warehouse`,
`airflow`, `spark`), mais le prototype les avait explicitement exclus par
nom en expliquant pourquoi (absents du profil de base), pas juste oubliés
— troisième confirmation de la même dynamique de propagation honnête.
Une vraie limite de qualité trouvée cette fois, différente d'une
invention : le prototype génère une liste plus généreuse/bruyante que la
curation minimaliste d'Erman (ajoute des termes génériques comme `python`,
`sql`, `django` que la vraie liste exclut délibérément).

**Prompt de la brique 3 resserré (2026-08-15)** — règle ajoutée pour
exclure les langages/frameworks/bases de données à usage général (sauf si
le rôle cible EST cette technologie), avec une catégorie de sortie dédiée
(`excluded_too_generic`). Re-testé sur le même rôle (Data Engineer) : le
bruit générique disparaît bien de la liste finale. **Un vrai bug de
compréhension trouvé et corrigé en cours de route** : `data warehouse`
s'était glissé dans les mots-clés alors que le profil dit explicitement
qu'il est *absent* — le modèle avait capté la présence du terme sans
percevoir la négation. Règle 1 renforcée en conséquence, re-testé, corrigé.
Un deuxième test à l'aveugle (rôle "Data Scientist", jamais consulté)
confirme l'amélioration mais révèle une limite plus fine encore ouverte :
les termes de méthode/processus statistique ("hypothesis testing",
"correlation analysis"...) devraient suivre la même règle que les
langages génériques — laissé pour une prochaine itération, pas traité
maintenant, pour ne pas tourner en boucle sur un seul prototype. Le
mécanisme anti-invention, lui, n'a jamais failli sur aucun des 3 rôles
testés. Détail complet : `prototypes/matching-keywords/output/RESULTS.md`.

**Clarification actée (2026-08-14) sur le ratio auto-envoi / validation
manuelle**, pour ne pas créer d'attente fausse : aujourd'hui, tout ce que la
*découverte automatique* trouve (ATS + alertes email) finit en validation
manuelle (`channel="platform"`), jamais en auto-envoi — une offre découverte
n'a jamais l'email direct d'un recruteur, seulement un lien de candidature.
L'auto-envoi ne s'applique qu'aux candidatures où l'utilisateur fournit
lui-même l'email du recruteur. Conséquence assumée du principe posé dès le
début (jamais de soumission automatique sur une plateforme tierce), pas un
défaut à corriger.

- [x] **Schéma de données PostgreSQL** (2026-08-14) — proposé et documenté
      dans `docs/schema.sql` (DDL complet) et `docs/DATA_MODEL.md`
      (correspondance fichier Phase 1 → table, décisions expliquées : la
      dédup d'offres devient une contrainte `UNIQUE` au lieu d'un fichier
      relu à la main, les rôles deviennent propres à chaque utilisateur au
      lieu d'une liste globale fixe, la lettre envoyée est figée au moment
      de l'envoi). Un point resté ouvert et explicitement non tranché : le
      stockage des secrets (mots de passe IMAP, tokens Gmail) par
      utilisateur — à décider avant d'implémenter `discovery_sources`.
**Tranché et implémenté le 2026-08-15** : chiffrement applicatif
(`backend/app/core/crypto.py`, Fernet), testé en réel (roundtrip correct,
mauvaise clé rejetée proprement). Détail : `docs/DATA_MODEL.md`.
- [x] **Backend FastAPI + PostgreSQL — démarré et testé en réel (2026-08-15)**,
      `backend/` — même SoC que `engine/` (routers/services/repositories/models/schemas/core).
      `docs/schema.sql` reste la source de vérité : la migration Alembic
      initiale l'exécute directement plutôt que de le retraduire en
      opérations une par une (`backend/alembic/versions/0001_initial_schema.py`).
      Modèles SQLAlchemy écrits pour les 14 tables du schéma. Premier
      vertical slice construit et **vérifié par de vraies requêtes HTTP
      contre une vraie base Postgres locale, pas des mocks** : `/health`,
      `/auth/signup`, `/auth/login`, `/auth/me` (JWT). Cas d'échec
      vérifiés aussi : sans jeton → 401, email déjà pris → 409, mauvais
      mot de passe → 401. Profil créé en cascade à l'inscription. Un bug
      de dépendance manquante trouvé et corrigé au passage
      (`pydantic[email]`, sinon `EmailStr` casse au démarrage). Détail :
      `backend/README.md`.
- [x] **Les 4 briques d'onboarding branchées au backend (2026-08-15)** —
      `POST /onboarding/cv-uploads` (upload + brique 1), `POST /onboarding/merge`
      (brique fusion), `GET`/`PATCH /onboarding/draft` + `POST /onboarding/draft/confirm`
      (relecture obligatoire, matérialise `experiences`+`profiles`),
      `POST /onboarding/roles` (brique adaptation + brique mots-clés,
      écrit `role_experience_bullets`/`role_projects`/`roles.keywords`).
      **Parcours complet testé en réel** : deux vrais CV d'Erman, vrais
      appels OpenRouter, upload → fusion (a détecté 2 désaccords que le
      test prototype isolé n'avait pas trouvés — variabilité normale d'un
      LLM) → confirmation bloquée tant que non résolus (409, vérifié) →
      relecture → confirmation → génération de 2 rôles, chacun avec ses
      bullets et projets correctement écrits en base.
      **Trois bugs réels trouvés et corrigés en testant** : colonnes
      `TIMESTAMPTZ` traitées comme naïves par SQLAlchemy (cassait la
      confirmation du draft), `max_tokens` trop bas pour le prompt resserré
      de la brique mots-clés (JSON tronqué), et le schéma `key_projects`
      de la brique adaptation qui avait perdu `subtitle`/`year` en portant
      le prototype. Détail complet : `backend/README.md`.
- [x] **Génération du `.docx` final branchée et testée en réel (2026-08-15)** —
      `POST /onboarding/roles/{id}/generate-cv` + `GET .../cv` (téléchargement).
      Port de `engine/services/cv_generation_service.py` (Phase 1) adapté
      au modèle relationnel : `job_1`/`job_2` fixes deviennent une boucle
      sur les expériences liées au rôle, "un seul projet" devient une
      boucle sur `role_projects` (plusieurs projets possibles, amélioration
      par rapport à la Phase 1). Réutilise `cv_style.py` tel quel (copié
      dans `backend/app/`, aucune logique métier dedans). **Parcours
      complet testé de bout en bout** : upload → fusion → confirmation →
      création de rôle → génération → téléchargement → fichier `.docx`
      réel, valide, relu et vérifié section par section. Régénération sur
      le même rôle → version passe correctement à 2. `roles.status` passe
      à `cv_ready` seulement une fois le fichier réellement généré (avant,
      il était marqué `cv_ready` dès la création du rôle — incohérence
      trouvée et corrigée au passage). **Limite assumée, pas un oubli** :
      les données personnelles sensibles (nationalité, statut de visa)
      des CV sources ne sont pas reportées dans le CV généré — `profiles`
      n'a pas de champ dédié pour ça aujourd'hui ; à trancher explicitement
      si on veut les rendre disponibles. Détail : `backend/README.md`.
      Reste à construire : découverte, candidatures, paiement.
- [x] **Frontend Next.js — onboarding + génération de CV branchés (2026-08-15)**,
      `frontend/` (Next.js 16 App Router, Tailwind v4). Design repris tel
      quel de la maquette validée le 2026-08-14 (tokens dans `globals.css`,
      aucune réinvention). Pages : `/login`, `/signup`, `/onboarding`
      (les 4 briques + génération/téléchargement de CV sur un seul écran,
      auth gérée par un contexte React + jeton JWT en localStorage).
      `npm run build` passe sans erreur (TypeScript inclus), rendu serveur
      vérifié par requêtes HTTP réelles.

      **Test interactif de bout en bout complété (2026-08-15)** — Chromium
      headless piloté par Playwright : inscription → upload d'un vrai CV
      → fusion → confirmation → création de rôle → génération →
      **téléchargement réel du `.docx` via un clic de navigateur**, fichier
      récupéré et vérifié. Même niveau d'exigence que `engine/`,
      `prototypes/` et `backend/`. Un bug trouvé au premier passage, mais
      dans le script de test, pas dans l'application : une syntaxe de
      sélecteur Playwright invalide faisait échouer l'étape "création de
      rôle" ; vérification en base a confirmé que le rôle avait bien été
      créé côté backend — corrigé, rejoué avec succès. Détail :
      `frontend/README.md`.

      L'écran de relecture du profil utilise un textarea JSON brut plutôt
      que l'édition champ par champ de la maquette — fonctionnel, moins
      soigné, à raffiner. Reste à construire : dashboard de suivi des
      candidatures (Phase 2, pas encore scopé côté découverte/candidatures).
- [x] Auth (JWT + bcrypt) — voir item backend ci-dessus, testé en réel le 2026-08-15
- [x] **Bêta sur invitation (2026-08-15)** — le produit déployé n'avait
      aucun mécanisme d'invitation ; n'importe qui trouvant l'URL pouvait
      s'inscrire, contredisant la décision du 2026-08-14 ("juste moi et
      quelques testeurs invités, mais prêt pour le public à tout moment").
      Table `beta_invites` + vérification dans `/auth/signup`
      (`NotInvitedError` → 403, distinct d'un email déjà pris → 409, pour
      la bonne sémantique HTTP). Un flag `BETA_INVITE_ONLY` (défaut `true`)
      -- **passer à l'ouverture publique ne demande de changer ni le code
      ni le schéma**, juste ce réglage. Gestion des invitations via
      `/admin/beta-invites` (POST/GET), protégé par un secret partagé
      (`ADMIN_TOKEN`) généré neuf pour la prod.

      **Testé en réel avant déploiement** (signup rejeté sans invitation,
      admin sans jeton rejeté, admin avec jeton accepté, signup accepté
      après invitation) **puis en production** : un inconnu au hasard
      rejeté (403), `ewilliantagain@gmail.com` invité avec succès — premier
      testeur, en attente qu'il crée lui-même son compte (mot de passe
      jamais choisi à sa place).
- [x] **Recherche automatique portée au web (2026-08-15)** — le plus gros
      morceau manquant identifié dans le calcul de "% prêt pour la mise en
      ligne" : jusqu'ici, la découverte (Phase 1.5) tournait uniquement en
      CLI (`engine/`), le produit web ne faisait que générer des CV. Port
      des Adapters ATS (Greenhouse/Lever — API publiques, aucune donnée
      d'authentification requise, aucune violation de CGU) et du matching
      par mots-clés dans `backend/`. Nouvelles tables déjà prêtes dans le
      schéma initial (`discovery_sources`, `postings`) enfin consommées.
      3 endpoints : ajouter une entreprise à surveiller, lancer une
      recherche, lister les candidatures trouvées (canal plateforme
      uniquement — jamais d'auto-envoi, même règle qu'en Phase 1.5).
      **Testé en réel à l'échelle**, backend puis navigateur : Palantir +
      Stripe, 886 offres examinées, 7 candidatures pertinentes mises en
      file (scores 3-4, cohérent avec les seuils Phase 1). Dédoublonnage
      vérifié sur relance immédiate : 0 nouvelle offre, 0 doublon, malgré
      886 offres re-récupérées — la contrainte `UNIQUE` du schéma
      (`INSERT ... ON CONFLICT DO NOTHING`) élimine par construction le bug
      de doublon intra-passage trouvé en Phase 1.5, pas besoin de le
      recorriger ici. Frontend : nouvelle page `/discovery`, parcours
      complet (inscription → onboarding → ajout d'une source → recherche →
      candidatures affichées) validé par un vrai navigateur (Playwright),
      capture d'écran à l'appui.

      **Scope explicitement limité aux sources ATS pour cette itération** —
      Gmail et IMAP restent CLI-only : Gmail demande un flux OAuth par
      utilisateur côté web (pas construit, différent du flux CLI existant),
      IMAP demande une UI de saisie de mot de passe branchée sur le
      chiffrement déjà construit (`app/core/crypto.py`, pas encore
      consommé). Prochaine itération, pas un oubli.
- [x] **Politique de confidentialité minimale (2026-08-15)** — `frontend/src/app/confidentialite/`,
      décrit exactement ce que le produit fait aujourd'hui (pas des
      promesses en avance sur le code) : données collectées, sous-traitants
      réels (OpenRouter, Railway, Greenhouse/Lever), ce qu'on ne fait
      jamais (auto-envoi plateforme, contenu inventé, secret en clair),
      droits, absence de tracking. Lien depuis l'inscription. À tenir à
      jour à chaque changement réel de traitement de données, pas figée.
- [ ] Paiement (Stripe, confirmé) — abonnement ou crédit par candidature
- [x] **Isolation des données par utilisateur — vérifiée en réel (2026-08-15)**,
      pas juste supposée du schéma (`user_id` partout). Deux vrais comptes
      créés (A, B) ; A onboardé complètement (CV réel, profil confirmé,
      rôle, `.docx` généré) ; B a tenté d'accéder aux ressources de A par
      tous les chemins de lecture existants — liste des CV uploadés, draft,
      liste des rôles, téléchargement du CV de A via son `role_id` réel,
      et déclenchement d'une régénération sur ce même rôle. **Aucune fuite
      détectée** : chaque tentative de B renvoie soit une liste vide, soit
      404 ("introuvable"), jamais le contenu de A. A garde un accès normal
      à ses propres ressources en parallèle.
- [x] **Onboarding — d'où viennent les infos d'un nouvel utilisateur** —
      question de l'utilisateur (2026-08-14) : pour Erman, `profile.json` et
      `cv_content.json` ont été construits à la main, via de vraies
      conversations — rien de généralisable à un inconnu tel quel. Sans
      mécanisme d'onboarding, un nouvel utilisateur ne peut littéralement pas
      utiliser le produit.

      **Décision retenue (2026-08-14)** : upload + complément court, pas un
      formulaire structuré complet — un formulaire de 40 champs reproduirait
      exactement la friction que le produit existe pour éliminer (voir
      "Pourquoi ça existe" — quelqu'un d'épuisé à 16h30 n'a pas l'énergie de
      retaper toute sa carrière à la main). Séquence :
      1. Upload du CV existant (PDF/Word) → extraction automatique vers le
         même format que `cv_content.json`/`profile.json`.
      2. Complément minimal — pas un formulaire complet, juste : quels types
         de poste cibler (définit les variantes de rôle, l'équivalent des 17
         rôles d'Erman) + un champ libre optionnel pour ce qui manque au CV.
      3. **Écran de relecture obligatoire, non contournable** — avant que
         quoi que ce soit serve à générer un CV ou une lettre, l'utilisateur
         voit exactement ce qui a été extrait/déduit et corrige. Même
         principe que le dry-run avant `--send` en Phase 1 : jamais d'action
         basée sur du contenu que la personne n'a pas explicitement validé.

      Explicitement écarté : import automatique depuis LinkedIn — reviendrait
      à scraper une plateforme tierce, exactement ce qu'on refuse déjà de
      faire pour la candidature elle-même.
- [x] **Exécution côté serveur (Railway) — déployé et validé en réel (2026-08-15)**,
      indépendante de la machine de l'utilisateur — **c'est ici,
      architecturalement, que se résout "ça tourne même machine éteinte"**,
      pas en Phase 1. Un cron local ne peut structurellement pas garantir
      ça pour un utilisateur tiers ; un backend qui tourne 24/7 sur un
      serveur, si. Cette clarification vient de l'utilisateur (2026-08-14) :
      la question du cron local vs cloud posée en Phase 1 était mal posée.

      Débloqué par l'utilisateur (`railway login`, authentification
      interactive que je ne pouvais pas faire à sa place), puis déployé de
      bout en bout via la CLI : projet + Postgres + service backend, projet
      + service frontend, variables de production (clés neuves, jamais
      celles de dev), CORS bouclé sur l'URL réelle du frontend. **Backend
      et frontend tous les deux en ligne**, parcours complet (inscription →
      upload CV → fusion → confirmation → rôle → génération → téléchargement)
      **vérifié par un vrai navigateur contre les vraies URL de production**,
      fichier `.docx` réel téléchargé et confirmé valide.

      **Deux vrais bugs trouvés en déployant, invisibles en local** :
      1. La migration initiale référençait `docs/schema.sql` en dehors de
         `backend/` — absent du contexte de build Railway (qui n'upload
         que le dossier `backend/`), jamais vu en local où tout le
         monorepo est sur disque. Corrigé en copiant le schéma dans
         `backend/db_schema.sql` (même raisonnement que `cv_style.py`).
      2. Nixpacks choisissait Node 18 par défaut, Next.js 16 exige Node
         ≥ 20.9 — `package.json` n'avait pas de champ `engines`. Corrigé.

      Détail complet, y compris les URL de production et deux comptes de
      test restés en base (pas de clé SSH pour les nettoyer, dit
      explicitement) : `DEPLOY.md`.

      **Stockage persistant corrigé (2026-08-15)**, avant d'inviter des
      testeurs — demandé explicitement par l'utilisateur. Volume Railway
      attaché au service backend, monté au même chemin qu'en local
      (`/app/storage`) — zéro changement de code. **Testé en réel, pas
      supposé** : CV généré → redéploiement forcé
      (`railway redeploy`) → même fichier retéléchargé, identique octet
      pour octet. Avant ce correctif, un redéploiement effaçait
      silencieusement tous les CV de tous les utilisateurs — jamais arrivé
      en pratique (trouvé et corrigé avant qu'un vrai testeur en fasse les
      frais). Limite assumée : un volume ne scale pas à plusieurs
      instances du service — S3/R2 reste l'étape suivante avant de scaler
      horizontalement, sans changer `core/storage.py`.
- [x] **Onboarding — quatre bugs réels trouvés en testant avec un compte
      réutilisé, corrigés (2026-08-15)** — jusqu'ici, tous les tests
      automatisés (Playwright) créaient un compte neuf à chaque fois ; ces
      bugs n'existaient que pour un utilisateur qui revient sur un compte
      déjà onboardé, exactement le cas d'un vrai testeur invité
      (`ewilliantagain@gmail.com`). Trouvés par l'utilisateur en testant en
      direct, pas par moi :
      1. **Onboarding verrouillé en permanence après une première
         confirmation** — le bouton d'upload et le bouton de fusion
         disparaissaient tous les deux dès que le profil passait à
         "confirmé", sans jamais revenir, même après rechargement. Corrigé :
         conditions d'affichage revues dans
         `frontend/src/app/onboarding/page.tsx`.
      2. **Bouton "Mettre à jour mon profil" visible mais grisé** — la
         correction du bug 1 rendait le bouton visible, mais sa propre
         condition `canMerge` bloquait quand même le clic après
         confirmation (`draft.status !== "confirmed"` redondant avec l'état
         qu'on cherche justement à autoriser). Corrigé en simplifiant
         `canMerge` à la seule présence d'un CV extrait.
      3. **Pas moyen de retirer un CV déjà uploadé** — demandé par
         l'utilisateur pour libérer une place sous le plafond de 3.
         `DELETE /onboarding/cv-uploads/{id}` + bouton "✕" par CV. N'affecte
         jamais un profil déjà confirmé (`confirm_draft` a déjà copié ce
         qu'il fallait dans `experiences`/`profiles`, indépendamment de
         l'upload source).
      4. **Étape 2 (relecture) et Étape 3 (rôles) restaient figées sur
         d'anciennes données après suppression de tous les CV** — signalé
         par l'utilisateur, confirmé volontaire une fois expliqué (le
         profil confirmé et les rôles sont *déjà* indépendants des uploads
         bruts, précisément pour ne jamais abîmer une candidature déjà
         envoyée), mais l'absence d'un moyen explicite de repartir à zéro
         était un vrai manque. Deux actions séparées ajoutées sur
         recommandation, approuvées par l'utilisateur ("Oui, vas-y") :
         - `DELETE /onboarding/profile` — vide CV uploadés + draft, ne
           touche **jamais** aux rôles déjà créés (bouton "Réinitialiser
           mon profil").
         - `DELETE /onboarding/roles/{id}` — suppression ciblée d'un rôle
           précis, y compris son `.docx` généré (bouton "✕" par rôle).

      **Bug critique trouvé en construisant ce correctif, avant qu'un
      testeur ne le déclenche** : `role_repository.replace_experiences`
      supprimait puis recréait toutes les lignes `experiences` à chaque
      confirmation — or `role_experience_bullets.experience_id` a
      `ON DELETE CASCADE`, donc reconfirmer son profil après avoir créé un
      rôle effaçait silencieusement les bullets de ce rôle (le rôle restait
      visible, vidé de son contenu). Renommé et réécrit en
      `sync_experiences` : les expériences existantes (clé = poste +
      entreprise) sont mises à jour sur place, jamais supprimées ; seules
      les expériences réellement nouvelles sont ajoutées. **Vérifié en
      réel, pas juste relu** : rôle créé (2 bullets confirmés en base),
      deuxième CV uploadé, profil refusionné et reconfirmé — 2 bullets
      toujours présents après coup, 2 nouvelles expériences ajoutées en
      plus (jamais de perte).

      Les deux nouveaux endpoints ont ensuite été testés à trois niveaux :
      en local (`curl` contre Postgres local, avec vérifications SQL
      directes des cascades et des fichiers physiques), en production via
      `curl` sur un compte jetable, puis **par un vrai navigateur headless
      (Playwright) contre l'URL de production réelle** — inscription,
      upload, fusion, confirmation, création de rôle, suppression du rôle,
      réinitialisation du profil, captures d'écran à l'appui confirmant
      chaque état affiché correspond bien à ce que l'API renvoie.
- [x] **Résolution de désaccord en un clic (2026-08-15)** — demandé par
      l'utilisateur après avoir buté deux fois sur l'édition manuelle du
      JSON : "quand je modifie l'email et que je soumets ma relecture, je
      suis obligé de refusionner" (en fait pas nécessaire — la confirmation
      marche directement après une relecture soumise — mais l'édition
      manuelle d'un JSON imbriqué pour corriger 3 valeurs précises est
      suffisamment casse-gueule pour qu'il ait cru devoir tout recommencer).

      **Problème de fond trouvé avant de construire le bouton** : le
      `field` d'un conflit est du texte libre généré par le LLM de fusion,
      pas un chemin fiable — la preuve dans l'exemple réel de l'utilisateur
      lui-même : deux conflits différents partageaient le même
      `field` ("experiences[1].date_range" pour la date de début ET de fin
      séparément), et chaque candidat ne contenait qu'un **fragment**
      ("Aug 2022" au lieu de "Aug 2022 – Aug 2024"). Un bouton qui aurait
      bêtement écrit le candidat à ce chemin aurait écrasé la moitié de la
      date. Corrigé à la source : prompt de `cv_merge_service.py` (et son
      prototype `prototypes/cv-merge/merge_profiles.py`, gardés
      synchronisés) resserré pour exiger un chemin JSON strict
      (`contact.email`, `experiences[1].date_range`), un seul conflit par
      champ composite (jamais scindé en fragments), et la valeur COMPLÈTE
      du champ pour chaque candidat. **Vérifié avec un vrai appel LLM**,
      sur le scénario exact rapporté par l'utilisateur (2 CV avec email et
      dates Alnajm Alwardi contradictoires) : un seul conflit par champ,
      valeurs complètes.

      Frontend : chaque candidat d'un conflit est maintenant un bouton
      cliquable qui applique sa valeur directement dans le JSON de
      relecture (chemin résolu et vérifié avant écriture — si le chemin ne
      se résout pas dans le JSON courant, retombe silencieusement sur
      l'édition manuelle plutôt que de risquer une corruption). Un
      indicateur visuel (✓, vert) montre quel candidat est actuellement
      appliqué. L'utilisateur garde le contrôle total : cliquer ne fait
      qu'écrire dans le brouillon, il valide ensuite via "Confirmer mon
      profil" — même principe de validation explicite que partout ailleurs
      dans le produit.

      **Correctif immédiat, signalé par l'utilisateur en testant** : "je
      clique sur un désaccord, mais c'est quoi la suite ?" Deux boutons
      séparés ("Soumettre ma relecture" puis "Confirmer mon profil")
      cassaient la cohérence du parcours (ailleurs : une action, un
      résultat visible). Fusionnés en un seul bouton "Confirmer mon
      profil" qui soumet toujours la relecture courante avant de
      confirmer, plus un compteur "X/2 désaccord(s) résolu(s)" pour que
      l'effet d'un clic soit visible immédiatement.

      **Testé en réel à trois niveaux** : appel LLM direct (nouveau prompt,
      conflit conforme), pipeline complet en local (upload → fusion →
      clic sur un candidat → confirmation directe en un bouton, sans
      refusion), puis un vrai navigateur contre l'URL de production —
      capture d'écran à l'appui montrant les deux coches vertes et le JSON
      mis à jour.
- [x] **Découverte automatique -- deux trous trouvés en testant, corrigés
      (2026-08-15)** :
      1. Affichage d'une source en erreur cassé -- `discovery_service.run`
         écrit `{"error": ...}` dans `last_run_summary` sur échec, forme
         différente de `{found, new, queued}` sur un passage réussi ; le
         frontend lisait `.found`/`.queued` à l'aveugle sur les deux
         formes, affichant des nombres vides au lieu du message d'erreur.
         Corrigé, testé en réel (source Lever invalide reproduite, 404
         confirmé côté API, message affiché correctement).
      2. **Aucun moyen d'agir sur une candidature trouvée** -- signalé par
         l'utilisateur : "comment je sais ce que j'en ai fait ?" Une
         candidature "queued" n'avait ni lien cliquable vers l'offre
         réelle (l'URL vivait dans une chaîne `notes` non affichée), ni
         suivi de statut -- elle restait "queued" pour toujours. Ajouté :
         lien "Voir l'offre" (nouvel onglet, vers `posting_url`) et un
         suivi de statut à 7 états (`queued` → `sent` → `viewed` →
         `contacted` → `interview_scheduled` → `offer_received`/
         `rejected`, `PATCH /discovery/candidacies/{id}`, aucune règle
         d'enchaînement imposée -- c'est la réalité de l'utilisateur à
         décrire, pas une machine à états qu'on lui impose). `sent_at`
         posé une seule fois, jamais réécrit ensuite (même principe que
         `cover_letter_text`).

      Testé en réel à trois niveaux (local, production API, production
      vrai navigateur) pour les deux correctifs.
- [x] **Découverte automatique -- ajout d'entreprise sans connaître
      Greenhouse/Lever (2026-08-15)** — question de l'utilisateur en
      testant : "comment il va savoir que c'est Greenhouse ou Lever ? le
      plus souvent on ne connaît pas le nom des entreprises, on postule
      juste en fonction de son CV." Un vrai problème de conception, pas
      un détail d'affichage. Deux niveaux distingués et validés par
      l'utilisateur ("les deux, dans cet ordre") :
      1. **Construit maintenant** : liste de départ de 36 entreprises
         (`GET /discovery/known-companies`, `app/data/known_companies.py`)
         avec type ATS et board token déjà remplis, choisie par nom via
         un champ de recherche -- l'utilisateur ne voit plus jamais
         "Greenhouse" ni "board token" pour une entreprise connue. Chaque
         entrée vérifiée en réel (curl direct contre l'API publique
         correspondante, 200 + au moins un poste ouvert) avant d'être
         écrite -- délibérément non exhaustive plutôt qu'une couverture
         large non vérifiée. L'ajout manuel reste disponible, replié
         derrière un lien secondaire.
      2. **Pas construit, chantier séparé et plus large** : "je ne sais
         pas quelles entreprises viser du tout" -- demanderait une
         recherche par mots-clés/poste à travers de nombreux employeurs
         (API de recherche d'emploi tierce, type Adzuna), pas juste une
         liste pré-remplie. Nécessite de choisir un fournisseur, gérer
         une clé API, vérifier les conditions d'utilisation, valider la
         couverture réelle -- pas fait à la légère.

      Testé en réel en local puis en production (vrai navigateur) :
      recherche "Anthropic" (Greenhouse) et "Palantir" (Lever), les deux
      ajoutées avec le bon type sans jamais l'exposer à l'utilisateur.
- [x] **Adaptation par offre précise — pivot stratégique (2026-08-15)** —
      né d'une conversation franche, pas d'une simple demande de
      fonctionnalité. En testant `/discovery`, l'utilisateur a demandé
      "comment un comptable ou une femme de ménage sait quelles
      entreprises chercher ?" — vérifié en réel (curl direct contre les
      API publiques) : sur ~24 entreprises tech connues, un seul poste de
      réception trouvé au total, aucune entreprise d'hôtellerie/facilities
      sur Greenhouse/Lever. Conclusion honnête assumée : la découverte
      automatique ne sert structurellement que les profils tech/corporate
      — pas réparable en ajoutant des entreprises, la source de données
      elle-même ne couvre pas ces métiers.

      Ça a mené à la question centrale : **"je ne vois pas qui paierait
      pour ça"**. Réponse honnête donnée : le marché de l'adaptation de CV
      par IA est déjà occupé (Teal, Rezi, Enhancv, JobScan) ; l'avantage
      réel de ce système n'a jamais été la découverte d'offres (LinkedIn/
      Indeed ont une couverture qu'on ne peut pas égaler), mais la
      contrainte structurelle "jamais inventer un fait absent du CV
      source" — sauf qu'en creusant, l'adaptation se faisait par
      **catégorie de rôle générique** ("Data Analyst"), pas par offre
      précise comme le discours produit le laissait entendre. Écart réel
      entre la promesse et le code, corrigé plutôt que maquillé.

      **Construit** : `POST /onboarding/roles/from-posting` — colle titre
      + description complète d'une offre trouvée n'importe où (pas besoin
      de la liste de `/discovery`), génère un rôle adapté **et** son
      `.docx` en une seule action. Étape 3 de l'onboarding reformulée
      ("Colle une offre, obtiens ton CV") pour refléter ça, l'ancienne
      création par nom générique devenue option secondaire repliée.

      **Bug d'hallucination trouvé en testant honnêtement sur un profil
      non-tech** (CV de femme de ménage + vraie offre d'hôtellerie à Abu
      Dhabi, choisi précisément pour vérifier la promesse "marche pour
      n'importe quel métier" après la critique du biais de `/discovery`) :
      un terme de l'offre ("mini-bar") a fui dans un bullet du CV généré
      alors qu'il n'existait nulle part dans le CV source — la faille que
      toute l'architecture est censée empêcher, révélée seulement parce
      que le texte cible peut désormais être une offre entière et pas
      juste un nom de rôle court. Corrigé (prompt resserré, synchronisé
      entre `backend/` et le prototype), revérifié : le même terme
      n'apparaît plus dans le CV, et le système explique maintenant
      honnêtement l'écart dans les notes de couverture au lieu de
      l'inventer. Deux bugs annexes trouvés et corrigés au passage : plantage
      du téléchargement sur un nom de rôle contenant un tiret cadratin
      (encodage HTTP), et plantage en recréant un rôle de nom identique
      (désambiguïsation automatique ajoutée).

      Testé en réel à trois niveaux (local, production API, production
      vrai navigateur avec téléchargement réel) sur le scénario exact
      décrit ci-dessus. Repositionnement produit qui en découle, à
      discuter avec l'utilisateur : cette capacité, pas la découverte
      d'offres, devient l'argument central de vente.
- [x] **Bug d'extraction .docx trouvé en testant "Colle une offre, obtiens
      ton CV" — tableaux ignorés (2026-08-15)** — l'utilisateur a testé la
      nouvelle Étape 3 avec un vrai modèle de CV téléchargé en ligne
      ("Warehouse-Worker-Resume-Sample") et reçu "aucune expérience ni
      compétence identifiable", alors qu'il avait bien rempli le fichier.
      Cause trouvée en reproduisant avec un CV de test à deux colonnes :
      `storage.extract_text()` ne lisait que les paragraphes simples --
      tout texte dans un **tableau** (mise en page standard des modèles
      de CV gratuits : sidebar contact/compétences + colonne expérience)
      était silencieusement ignoré. Pas un cas limite rare : potentiellement
      une bonne partie des CV réels utilisant des modèles gratuits en
      ligne, exactement le public le plus susceptible de s'appuyer sur un
      modèle plutôt que de composer son CV depuis zéro.

      Corrigé (parcours paragraphes + tableaux dans l'ordre réel
      d'apparition), testé en réel : pipeline complet (upload → extraction
      → fusion) sur un CV de test à deux colonnes, contact/compétences/
      certification/2 expériences avec bullets/formation tous correctement
      extraits, en local puis en production (le déploiement a mis un peu
      de temps à se propager -- deuxième `railway up` nécessaire, vérifié
      après coup en réextrayant le même fichier).
- [x] **Point 2 en cours — auto-envoi email, comptes email connectés et
      validés en réel (2026-08-16)** — suite du plan en 4 points discuté
      avec l'utilisateur pour rendre le produit vendable. Décision
      tranchée : envoyer depuis la propre boîte mail de l'utilisateur
      (SMTP, ses identifiants), pas un domaine partagé -- plus crédible
      pour le recruteur, ne dépend d'aucune vérification de domaine côté
      fournisseur d'envoi.

      **Construit** : `POST/GET/DELETE /email-accounts`, connexion
      IMAP vérifiée avant tout enregistrement (échec = rien stocké),
      mot de passe chiffré (`core/crypto.py`, jamais en clair, jamais
      renvoyé). `imap_adapter.py` porté de Phase 1, `smtp_adapter.py`
      nouveau (dry-run par défaut partout, même principe que Resend en
      Phase 1 -- jamais d'envoi réel sans geste explicite déjà vérifié).
      Section "Ton compte email" sur `/discovery`.

      **Testé en réel, chemin d'erreur ET chemin de succès** : erreur
      vérifiée contre un vrai serveur IMAP (mot de passe volontairement
      faux, rejet propre, 0 ligne en base) ; succès validé par
      l'utilisateur lui-même en production, avec ses propres identifiants
      (`ermanwilliantag@tensoratech.com`) -- jamais partagés dans la
      conversation, compte toujours présent après rechargement de page
      (vraie persistance confirmée, pas un affichage optimiste). Bug
      annexe trouvé par l'utilisateur et corrigé dans la foulée : libellé
      et adresse email affichés collés (marge CSS sans espace réel dans
      le texte) -- même défaut corrigé à 2 autres endroits de la page.

      **Pas encore construit** (reste du point 2) : découverte par
      alertes email (port d'`email_alert_service.py`, Phase 1), génération
      de lettre de motivation (brique absente du web aujourd'hui),
      endpoint d'envoi réel avec aperçu avant confirmation.
- [ ] **Vérification OAuth Google (bloquant pour Gmail multi-utilisateur)** —
      question de l'utilisateur (2026-08-14) : est-ce que le système gère
      n'importe quelle boîte email d'un futur utilisateur, pas seulement les
      comptes de test actuels ? Réponse honnête : le code oui
      (`gmail_adapter.py` accepte n'importe quel compte), mais l'app Google
      Cloud est en statut "Testing", plafonnée à 100 utilisateurs ajoutés à
      la main un par un (`Error 403: access_denied` sinon — vécu en réel
      pendant cette session). Pour qu'un utilisateur inconnu authentifie son
      Gmail sans qu'on l'ajoute manuellement, l'app doit passer la
      **vérification Google** (politique de confidentialité, revue de
      sécurité possible vu que `gmail.readonly` est un scope sensible) —
      un vrai chantier, pas une case à cocher. L'IMAP générique n'a pas ce
      problème (déjà validé sur un hébergeur tiers, `tensoratech.com`).

      **Stratégie retenue (2026-08-14)** : ne pas bloquer le développement
      sur la vérification Google. Bêta privée avec un petit groupe de
      testeurs (chacun ajouté manuellement dans Test users — jusqu'à 100),
      pendant qu'on continue à construire les phases restantes. La
      vérification Google n'est demandée qu'une fois l'application
      complètement fonctionnelle et stable — vérifier trop tôt serait
      contre-productif si l'app change encore beaucoup. Suivi des testeurs :
      `data-erman/beta_testers.json`.
- [ ] Déclenchement du pipeline sans commande — aujourd'hui la découverte
      se lance en tapant une commande CLI, même pour l'utilisateur actuel.
      "Le système part chercher tout seul" pour un utilisateur final suppose
      l'exécution serveur (item ci-dessus), pas juste l'accès à sa boîte mail.

**Exigence produit non négociable (Phase 2)** : le design doit être soigné et
professionnel — pas un formulaire brut. Les gens paient parce que le produit
est agréable à utiliser et qu'ils y voient une valeur ajoutée claire, pas
uniquement parce qu'il fonctionne. Un travail de design réel est prévu avant
tout lancement payant (skill `dataviz`/`artifact-design` comme point de départ
pour le langage visuel, à affiner).

**Direction visuelle validée (2026-08-14)** — maquette combinant les deux
premiers écrans (onboarding + tableau de bord), validée par l'utilisateur
("j'aime bien la direction, on part là-dessus"). Sert de référence pour
toute l'implémentation Next.js à venir — pas à redeviner à chaque écran :
- **Métaphore** : instrument de navigation ("autopilot") — précision, calme,
  contrôle, pas un dashboard SaaS générique.
- **Palette** : encre marine (`#12182A`) + teal instrument (`#1F6E7C`,
  `#62B4C0` en sombre) + touche laiton pour les alertes (`#B8791F`) — jamais
  de crème/terracotta ni de vert acide sur noir (clichés de design généré
  par IA explicitement évités).
- **Typo** : serif display (Iowan Old Style/Palatino/Georgia) pour les
  titres, sans-serif géométrique (Avenir Next/Segoe UI) pour l'interface,
  monospace (SF Mono/Cascadia/Consolas) pour toute donnée chiffrée (scores,
  dates, compteurs) — `font-variant-numeric: tabular-nums` partout où des
  chiffres s'alignent en colonne.
- **Layout** : deux écrans qui se répondent, reliés par une ligne de
  navigation en pointillés (fil conducteur "autopilot"), thèmes clair/sombre
  tous les deux traités avec le même soin (jamais une simple inversion).
- Maquette de référence : publiée via Artifact le 2026-08-14 (upload CV →
  relecture obligatoire → cibles de rôle → génération ; puis tableau de bord
  à 3 colonnes reflétant les vrais états — À valider / Envoyée / Répondu,
  avec les vraies données : 19 entreprises, 2 boîtes mail, Cobblestone
  Energy comme seule candidature réellement envoyée).

---

## Stack

Suit la carte "SaaS complet" de `TOOLS/MA_STACK_PERSONNELLE.md` :

```
Frontend    → Next.js 16 + Tailwind (phase 2)
Backend     → FastAPI (Python)
Base de données → PostgreSQL (+ pgvector si matching sémantique offre↔CV plus tard)
Email       → Resend
Auth        → JWT + bcrypt (phase 2)
Paiement    → Stripe (phase 2)
Hébergement → Railway
```

---

## Options futures (idées, rien d'engagé)

Non planifiées, non chiffrées — à évaluer une par une le moment venu, pour ne
pas gonfler artificiellement le scope de la Phase 2 :

- **Détection des réponses** — lire les réponses entrantes des recruteurs
  (email) pour mettre à jour le statut automatiquement, au lieu de le faire
  à la main dans le tracker.
- **Matching sémantique** — remplacer/compléter le scoring par mots-clés par
  des embeddings (pgvector, déjà dans la stack) pour mieux juger la
  pertinence d'une offre.
- **Portfolio généré automatiquement** — en plus du CV, une page/portfolio
  adaptée au poste visé (mentionné par l'utilisateur, pas scopé).
- **Versions multilingues** — CV/lettres en français en plus de l'anglais,
  pertinent vu le positionnement bilingue déjà présent dans le profil.
- **A/B testing des CV** — suivre quelle variante d'un même rôle obtient le
  plus de réponses, ajuster automatiquement.
- **Extension navigateur** — "postuler avec CV Autopilot" en un clic depuis
  une page d'offre, pour les cas où l'utilisateur navigue lui-même.
- **Mode agence / coach carrière** — un compte gère plusieurs candidats
  (angle B2B, différent du B2C individuel).
- **Prépa entretien** — rappels ciblés (banque de questions déjà présente
  dans `Interview_QA_Erman_Tagaintchuem.md`) quand un entretien est détecté
  dans le tracker.
- **Profil maître comme base de connaissance élargie** (idée reprise d'une
  discussion externe, 2026-08-14) — au-delà du CV et de la lettre, la même
  donnée pourrait générer un résumé LinkedIn ou une analyse d'écart de
  compétences par rapport à une offre. Non prioritaire : les 3 briques
  d'extraction/adaptation/matching passent avant toute nouvelle
  fonctionnalité consommant le profil.
- **Intégrations** — Zapier/API publique pour utilisateurs avancés qui
  veulent brancher leurs propres outils.

---

## Données de référence (client zéro : Erman)

Tout dans `data-erman/` — ancien dossier `FREELANCES/Career-cv/` :
- `profile.json` — source unique du profil
- `mapping-syllabus.md` — quel CV pour quel type d'offre
- `cover-letters.md` — templates de lettre par rôle
- `tracker-candidatures.md` — suivi + règles de relance
- `linkedin-guide.md` — synchronisation LinkedIn

---

*Statut (2026-08-14) : Phase 1 terminée et validée en conditions réelles.
Phase 1.5 — source ATS publics (Greenhouse/Lever) construite et testée en
réel. Reste : source alertes email (Phase 1.5), puis Phase 2.*
