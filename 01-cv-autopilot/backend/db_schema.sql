-- CV Autopilot — schéma PostgreSQL, Phase 2 (multi-tenant)
--
-- Copie de ../docs/schema.sql -- duplication délibérée (même raisonnement
-- que cv_style.py) : `railway up` lancé depuis backend/ n'embarque que ce
-- dossier, pas le reste du monorepo. Bug trouvé en déployant pour de vrai
-- le 2026-08-15 -- la migration initiale référençait ../../../../docs/schema.sql,
-- absent du contexte de build sur Railway (FileNotFoundError au démarrage).
-- ../docs/schema.sql reste la source de vérité pour la lecture/le
-- raisonnement (docs/DATA_MODEL.md) ; cette copie est ce que la migration
-- exécute réellement en production. Garder synchronisées à la main.
--
-- Remplace les fichiers par client (data-<client>/*.json, tracker-candidatures.md,
-- cover-letters.md, queue/) par des tables partagées, isolées par user_id.
-- Voir docs/DATA_MODEL.md pour la correspondance fichier -> table, poste par poste,
-- et les décisions prises en écrivant ce schéma.
--
-- Convention : toute table qui appartient à un utilisateur porte un user_id et
-- une contrainte ON DELETE CASCADE — supprimer un compte doit supprimer toutes
-- ses données, sans exception à traquer une par une.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";  -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "citext";    -- email insensible à la casse

CREATE TYPE channel_type AS ENUM ('email', 'platform');

-- Vocabulaire repris tel quel de tracker-candidatures.md (section "Statuts
-- possibles") -- ce sont déjà les statuts que l'utilisateur met à jour à la
-- main aujourd'hui, pas un vocabulaire réinventé pour la base de données.
CREATE TYPE application_status AS ENUM (
    'queued',              -- 🟡 préparée, canal plateforme, pas encore validée par l'humain
    'sent',                -- 📤 Envoyé
    'viewed',               -- 👀 Vue (profil consulté)
    'contacted',            -- 📞 Contacté par recruteur
    'interview_scheduled',  -- 🗓️ Entretien planifié
    'offer_received',       -- ✅ Offre reçue
    'rejected',              -- ❌ Refusé
    'follow_up_sent',       -- 🔄 Relance envoyée
    'waiting'                -- ⏳ En attente
);

CREATE TYPE source_type AS ENUM ('ats_greenhouse', 'ats_lever', 'gmail', 'imap');
CREATE TYPE source_status AS ENUM ('active', 'error', 'disabled');
CREATE TYPE extraction_status AS ENUM ('pending_review', 'confirmed', 'discarded');
CREATE TYPE cv_upload_status AS ENUM ('uploaded', 'extracting', 'extracted', 'failed');

-- ---------------------------------------------------------------------------
-- Identité
-- ---------------------------------------------------------------------------

CREATE TABLE users (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email               CITEXT UNIQUE NOT NULL,
    password_hash       TEXT,                       -- bcrypt ; NULL si login OAuth-only plus tard
    full_name           TEXT NOT NULL,
    stripe_customer_id  TEXT,
    plan                TEXT NOT NULL DEFAULT 'free',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Remplace profile.json. Les "contact_line_1/2" pré-formatées du fichier
-- actuel deviennent des champs structurés -- un raccourci de Phase 1 qu'on
-- corrige ici plutôt que de le reporter tel quel.
CREATE TABLE profiles (
    user_id           UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    headline          TEXT,                         -- ex: "Data Analyst"
    phone             TEXT,
    location          TEXT,
    linkedin_url      TEXT,
    github_url        TEXT,
    portfolio_url     TEXT,
    from_email        TEXT,                         -- adresse d'envoi vérifiée (Resend)
    target_countries  JSONB NOT NULL DEFAULT '[]',   -- ex: ["UAE", "Canada"]
    education         JSONB NOT NULL DEFAULT '[]',
    certifications    JSONB NOT NULL DEFAULT '[]',
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Onboarding -- upload + extraction + relecture obligatoire (PRODUCT.md,
-- décision du 2026-08-14). L'état "confirmed" est ce qui autorise la
-- génération de CV -- pas une case cochée côté UI seulement.
-- ---------------------------------------------------------------------------

CREATE TABLE cv_uploads (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    file_name    TEXT NOT NULL,
    storage_key  TEXT NOT NULL,                     -- objet S3/R2 -- jamais le binaire en DB
    mime_type    TEXT NOT NULL,
    size_bytes   INTEGER NOT NULL,
    status       cv_upload_status NOT NULL DEFAULT 'uploaded',
    uploaded_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Un upload = une extraction brute (brique 1, inchangée -- elle tourne par
-- document, jamais sur plusieurs CV concaténés). Décision du 2026-08-15 :
-- jusqu'à 3 CV à l'onboarding (voir DATA_MODEL.md pour le raisonnement).
CREATE TABLE cv_upload_extractions (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cv_upload_id   UUID NOT NULL REFERENCES cv_uploads(id) ON DELETE CASCADE,
    raw_extraction JSONB NOT NULL,   -- sortie brute de la brique 1 pour CE document -- jamais modifiée après coup
    extracted_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Un draft = LA vue fusionnée que l'utilisateur relit et valide -- un seul
-- écran de relecture, même si plusieurs CV ont été uploadés (pas un écran
-- par document). "conflicts" porte les désaccords entre documents sources
-- qu'une fusion automatique ne doit jamais trancher silencieusement (ex :
-- deux numéros de téléphone différents) -- l'utilisateur choisit, pas l'IA.
CREATE TABLE extracted_profile_drafts (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id              UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    raw_extraction       JSONB NOT NULL,             -- fusion des cv_upload_extractions -- jamais modifiée après coup
    reviewed_extraction  JSONB,                      -- après corrections de l'utilisateur
    conflicts            JSONB NOT NULL DEFAULT '[]', -- désaccords entre documents sources, à trancher par l'utilisateur
    status               extraction_status NOT NULL DEFAULT 'pending_review',
    confirmed_at         TIMESTAMPTZ
);

-- Traçabilité : quels uploads ont nourri quel draft fusionné.
CREATE TABLE draft_source_uploads (
    draft_id      UUID NOT NULL REFERENCES extracted_profile_drafts(id) ON DELETE CASCADE,
    cv_upload_id  UUID NOT NULL REFERENCES cv_uploads(id) ON DELETE CASCADE,
    PRIMARY KEY (draft_id, cv_upload_id)
);

-- ---------------------------------------------------------------------------
-- Contenu CV -- remplace cv_content.json + roles.json + cover-letters.md
-- ---------------------------------------------------------------------------

-- Un même poste, raconté différemment selon le rôle ciblé : dans
-- cv_content.json, "job_1"/"job_2" (titre/entreprise/dates) sont partagés
-- entre toutes les variantes, seuls "job1_bullets"/"job2_bullets" changent
-- par rôle. On garde cette séparation ici plutôt que de dupliquer le poste
-- à chaque rôle.
CREATE TABLE experiences (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id            UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    position_title     TEXT NOT NULL,
    company_location   TEXT NOT NULL,
    date_range         TEXT NOT NULL,
    sort_order         SMALLINT NOT NULL DEFAULT 0
);

-- Remplace roles.json + les entrées "roles.<id>" de cv_content.json +
-- cover-letters.md (une variante = un rôle = un CV = une lettre, plus de
-- numérotation partagée entre rôles comme aujourd'hui).
CREATE TABLE roles (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name                   TEXT NOT NULL,             -- ex: "ML / AI Engineer"
    keywords               JSONB NOT NULL DEFAULT '[]',
    summary                TEXT,
    skills                 JSONB NOT NULL DEFAULT '[]',
    cover_letter_template  TEXT,                      -- avec [PLACEHOLDERS]
    status                 TEXT NOT NULL DEFAULT 'draft',  -- draft / cv_ready
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, name)
);

CREATE TABLE role_experience_bullets (
    role_id        UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    experience_id  UUID NOT NULL REFERENCES experiences(id) ON DELETE CASCADE,
    bullets        JSONB NOT NULL DEFAULT '[]',
    sort_order     SMALLINT NOT NULL DEFAULT 0,
    PRIMARY KEY (role_id, experience_id)
);

CREATE TABLE role_projects (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_id     UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    subtitle    TEXT,
    year        TEXT,
    bullets     JSONB NOT NULL DEFAULT '[]',
    sort_order  SMALLINT NOT NULL DEFAULT 0
);

-- Un .docx généré, versionné -- remplace le fichier unique écrasé à chaque
-- regénération dans le système actuel.
CREATE TABLE cv_files (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_id       UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    storage_key   TEXT NOT NULL,
    version       INTEGER NOT NULL DEFAULT 1,
    generated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Découverte -- remplace discovery_watchlist.json + email_accounts.json +
-- imap_accounts.json + seen_postings.json
-- ---------------------------------------------------------------------------

CREATE TABLE discovery_sources (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id            UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type               source_type NOT NULL,
    label              TEXT NOT NULL,               -- ex: "Palantir", "aiengineernlp@gmail.com"
    config             JSONB NOT NULL DEFAULT '{}',  -- board_token/company_display_name, ou host/port/username IMAP
    credential_ref     TEXT,                        -- pointeur vers un secret -- JAMAIS le secret lui-même (voir DATA_MODEL.md)
    status             source_status NOT NULL DEFAULT 'active',
    last_run_at        TIMESTAMPTZ,
    last_run_summary   JSONB,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- La dédup vit dans la contrainte UNIQUE ci-dessous, plus dans un fichier
-- seen_postings.json relu/réécrit à la main -- élimine par construction le
-- bug de doublon intra-passage rencontré en Phase 1.5 (deux occurrences de
-- la même offre dans un même run ne peuvent plus survivre : la deuxième
-- INSERT échoue sur la contrainte).
CREATE TABLE postings (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id              UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    discovery_source_id  UUID REFERENCES discovery_sources(id) ON DELETE SET NULL,
    source               TEXT NOT NULL,              -- greenhouse / lever / indeed_alert / linkedin_alert
    external_id          TEXT NOT NULL,              -- clé stable (jk Indeed, id LinkedIn, hash de repli)
    company              TEXT NOT NULL,
    title                TEXT NOT NULL,
    location             TEXT,
    url                  TEXT,
    description          TEXT,
    discovered_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, source, external_id)
);

-- ---------------------------------------------------------------------------
-- Candidatures -- remplace tracker-candidatures.md + le dossier queue/
-- ---------------------------------------------------------------------------

CREATE TABLE applications (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    posting_id          UUID REFERENCES postings(id) ON DELETE SET NULL,  -- NULL si candidature manuelle
    role_id             UUID REFERENCES roles(id) ON DELETE SET NULL,
    cv_file_id          UUID REFERENCES cv_files(id) ON DELETE SET NULL,
    company             TEXT NOT NULL,
    title               TEXT NOT NULL,
    channel             channel_type NOT NULL,
    status              application_status NOT NULL DEFAULT 'queued',
    match_score         SMALLINT,
    recruiter_email     TEXT,
    recruiter_name      TEXT,
    cover_letter_text   TEXT,     -- figée au moment de l'envoi -- jamais régénérée rétroactivement
    storage_key         TEXT,     -- sujet + lettre + CV, pour le canal plateforme (équivalent de queue/<dossier>/)
    notes               TEXT,
    sent_at             TIMESTAMPTZ,
    follow_up_due_at    TIMESTAMPTZ,
    follow_up_sent_at   TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX applications_user_status_idx ON applications (user_id, status);
CREATE INDEX applications_follow_up_due_idx ON applications (user_id, follow_up_due_at) WHERE status = 'sent';
CREATE INDEX postings_user_discovered_idx ON postings (user_id, discovered_at DESC);

-- Bêta privée -- voir ../docs/schema.sql pour le commentaire complet.
-- Ajoutée par migration 0002, hors de ce fichier initial (0001) --
-- documenté ici uniquement pour que cette copie reste à jour.
CREATE TABLE beta_invites (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       CITEXT UNIQUE NOT NULL,
    invited_by  TEXT,
    invited_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
