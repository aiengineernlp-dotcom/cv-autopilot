"""Couche : Service — orchestrateur.

Fait : repère dans tracker-candidatures.md les candidatures "📤 Envoyé" dont la
date de relance (J+7) est atteinte, rédige la relance (letter_service), l'envoie
via l'Adapter Resend, puis met à jour la ligne (Repository tracker_repository).
C'est la pièce qui permet au produit de tourner sans intervention — appelée par
un cron (voir cli.py `run-followups`).
Ne fait jamais : lire/écrire tracker-candidatures.md lui-même (délègue au
Repository), parler à Resend directement (délègue à l'Adapter).
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from ..adapters import resend_adapter
from ..config import ClientConfig
from ..repositories import profile_repository, tracker_repository
from . import letter_service

DUE_STATUS = "📤 Envoyé"
SENT_STATUS = "🔄 Relance envoyée"


@dataclass
class FollowupResult:
    entreprise: str
    poste: str
    to: str
    sent: bool
    skipped_reason: str | None
    mailer_result: dict | None


def _is_due(values: dict, today: dt.date) -> bool:
    if values.get("Statut") != DUE_STATUS:
        return False
    relance = values.get("Relance le", "")
    if not relance:
        return False
    try:
        relance_date = dt.date.fromisoformat(relance)
    except ValueError:
        return False
    return relance_date <= today


def run(client: ClientConfig, *, today: dt.date | None = None, send: bool = False) -> list[FollowupResult]:
    today = today or dt.date.today()
    template_raw = tracker_repository.load_followup_template(client)
    profile = profile_repository.load_profile(client)
    from_email = profile["personal"]["email"]

    results: list[FollowupResult] = []

    for row in tracker_repository.list_rows(client):
        values = row.values
        if not _is_due(values, today):
            continue

        email = values.get("Email Recruteur", "")
        entreprise = values.get("Entreprise", "")
        poste = values.get("Poste", "")

        if not email:
            results.append(FollowupResult(entreprise, poste, "", False, "Pas d'email recruteur enregistré", None))
            continue

        placeholders = {
            "POSTE": poste,
            "ENTREPRISE": entreprise,
            "DATE": values.get("Date", ""),
            "NOM": values.get("Contact") or "there",
            "2-3 MOTS CLÉS DU RÔLE": poste,
        }
        text, unresolved = letter_service.render_text(template_raw, placeholders)
        subject_line, _, body = text.partition("\n")
        subject = subject_line.replace("Subject:", "").strip() or f"Follow-up — {poste} Application"
        body = body.strip()

        if unresolved:
            results.append(
                FollowupResult(entreprise, poste, email, False, f"Placeholders non résolus : {', '.join(unresolved)}", None)
            )
            continue

        mailer_result = resend_adapter.send(
            to=email, subject=subject, text=body, from_email=from_email,
            attachment_path=None, dry_run=not send,
        )
        sent = not mailer_result["dry_run"]

        if sent:
            tracker_repository.update_row(client, row.line_index, {"Statut": SENT_STATUS, "Relance le": ""})

        results.append(FollowupResult(entreprise, poste, email, sent, None, mailer_result))

    return results
