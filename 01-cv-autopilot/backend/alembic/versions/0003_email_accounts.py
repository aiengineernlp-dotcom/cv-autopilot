"""Comptes email pour la découverte par alertes (indeed_alert/linkedin_alert)
et l'auto-envoi canal email en boîte propre de l'utilisateur.

Décision produit du 2026-08-16 : porter la capacité "candidater pendant
que je dors" (Phase 1 CLI, validée sur tensoratech.com) vers le site pour
un utilisateur quelconque, pas seulement l'opérateur. Choix tranché avec
l'utilisateur : envoyer réellement depuis SA boîte mail (SMTP avec ses
identifiants), pas depuis un domaine partagé CV Autopilot -- plus fidèle
à "candidater soi-même", plus crédible pour le recruteur qui reçoit
l'email.

Le mot de passe ne vit JAMAIS en clair -- chiffré via app/core/crypto.py
(Fernet, déjà construit pour ce besoin, pas encore consommé avant
aujourd'hui). Un compte sert à la fois pour IMAP (lecture, découverte
d'alertes) et SMTP (envoi, mêmes identifiants dans l'immense majorité des
hébergeurs) -- deux couples host/port distincts, un seul mot de passe.

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-16
"""
from __future__ import annotations

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE email_accounts (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            label               TEXT NOT NULL,             -- ex: "erman@tensoratech.com"
            imap_host           TEXT NOT NULL,
            imap_port           SMALLINT NOT NULL DEFAULT 993,
            smtp_host           TEXT NOT NULL,
            smtp_port           SMALLINT NOT NULL DEFAULT 465,
            username            TEXT NOT NULL,
            encrypted_password  TEXT NOT NULL,              -- Fernet, voir app/core/crypto.py -- jamais en clair
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (user_id, label)
        );
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS email_accounts;")
