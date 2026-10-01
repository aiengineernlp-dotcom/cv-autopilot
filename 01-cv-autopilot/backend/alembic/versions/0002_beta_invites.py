"""Liste d'invitation pour la bêta privée.

Décision produit du 2026-08-14 : "juste moi et quelques testeurs invités,
mais prêt pour le public à tout moment". Le produit déployé n'avait aucun
mécanisme d'invitation -- n'importe qui trouvant l'URL pouvait s'inscrire,
contredisant l'objectif. Cette table + la vérification côté signup
comblent ça sans toucher au reste du schéma.

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-15
"""
from __future__ import annotations

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE beta_invites (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email       CITEXT UNIQUE NOT NULL,
            invited_by  TEXT,
            invited_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS beta_invites;")
