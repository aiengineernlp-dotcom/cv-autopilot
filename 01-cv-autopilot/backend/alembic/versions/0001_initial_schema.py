"""Schéma initial -- exécute backend/db_schema.sql directement.

db_schema.sql (copie de ../../../docs/schema.sql, voir son en-tête) est la
source de vérité déjà revue et validée (voir docs/DATA_MODEL.md pour le
raisonnement derrière chaque table) -- cette migration ne le retraduit pas
en opérations Alembic une par une, elle l'exécute tel quel pour éviter tout
risque de divergence entre les deux.

Chemin corrigé le 2026-08-15 (bug trouvé en déployant sur Railway pour de
vrai) : pointait vers docs/schema.sql, hors de backend/ -- absent du
contexte de build quand `railway up` est lancé depuis backend/ seul
(FileNotFoundError au démarrage, jamais vu en local où le monorepo entier
est présent sur disque).

Revision ID: 0001
Revises:
Create Date: 2026-08-15
"""
from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

SCHEMA_SQL_PATH = Path(__file__).resolve().parent.parent.parent / "db_schema.sql"


def upgrade() -> None:
    op.execute(SCHEMA_SQL_PATH.read_text(encoding="utf-8"))


def downgrade() -> None:
    op.execute("""
        DROP TABLE IF EXISTS applications, postings, discovery_sources, cv_files,
            role_projects, role_experience_bullets, roles, experiences,
            draft_source_uploads, extracted_profile_drafts, cv_upload_extractions,
            cv_uploads, profiles, users CASCADE;
        DROP TYPE IF EXISTS cv_upload_status, extraction_status, source_status,
            source_type, application_status, channel_type;
    """)
