"""Couche : Service — orchestrateur.

Fait : traite une candidature de bout en bout — appelle matching_service et
letter_service (logique), puis les Repositories (roles, cover-letters, tracker,
profile, queue) et l'Adapter Resend (I/O). C'est le seul fichier autorisé à faire
parler plusieurs Repositories/Adapters entre eux.
Ne fait jamais : lire/écrire un fichier lui-même (délègue toujours au Repository
concerné), afficher quoi que ce soit (couche UI/cli.py), parler à Resend directement
(délègue à l'Adapter).
"""
from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from pathlib import Path

from ..adapters import resend_adapter
from ..config import ClientConfig
from ..repositories import cover_letter_repository, profile_repository, queue_repository, roles_repository, tracker_repository
from . import letter_service, matching_service

CANADA_MOBILITY_NOTE = (
    "\n\nI am eligible to work in Canada without employer LMIA under the Francophone "
    "Mobility Program (Code C16). Express Entry profile: E004992217."
)

_SLUG_RE = re.compile(r"[^a-zA-Z0-9]+")


def _slugify(text: str, max_len: int = 40) -> str:
    slug = _SLUG_RE.sub("_", text).strip("_")
    return slug[:max_len] or "sans_titre"


class ApplicationError(RuntimeError):
    """Erreur métier (rôle inconnu, CV manquant, template manquant...) — jamais une erreur technique brute."""


@dataclass
class ApplicationResult:
    role: roles_repository.Role
    match_score: int
    forced_role: bool
    subject: str
    body: str
    unresolved_placeholders: list
    sent: bool
    queued_to: Path | None
    mailer_result: dict | None


def _select_role(client: ClientConfig, *, role_id: str | None, title: str, description: str):
    roles = roles_repository.load_roles(client)
    if role_id:
        role = roles_repository.find_by_id(client, role_id)
        if role is None:
            raise ApplicationError(f"Rôle inconnu : {role_id}")
        return role, 0, True
    result = matching_service.match(title, description, roles)
    if result.role is None:
        raise ApplicationError("Aucun rôle ne matche cette offre (score 0 partout). Précise role_id.")
    return result.role, result.score, False


def process(
    client: ClientConfig,
    *,
    company: str,
    title: str,
    description: str,
    channel: str,
    country: str,
    recruiter_email: str | None,
    recruiter_name: str | None,
    role_id: str | None,
    from_email: str | None,
    send: bool,
    force: bool,
    notes: str,
) -> ApplicationResult:
    role, match_score, forced_role = _select_role(client, role_id=role_id, title=title, description=description)

    if role.status != "cv_disponible" and not force:
        raise ApplicationError(f"Pas de CV généré pour '{role.name}' — {role.notes or 'à créer avant de postuler.'}")

    cv_path = (client.root / role.cv_path) if role.cv_path else None

    templates = cover_letter_repository.load_templates(client)
    template = templates.get(role.cover_letter_number)
    if template is None:
        raise ApplicationError(f"Pas de template de lettre #{role.cover_letter_number} dans cover-letters.md")

    placeholders = {
        "TITRE DU POSTE": title,
        "ENTREPRISE": company,
        "NOM DU RECRUTEUR ou Hiring Team": recruiter_name or "Hiring Team",
    }
    letter_text, unresolved = letter_service.render(template, placeholders)
    subject_line, _, body = letter_text.partition("\n")
    subject = subject_line.replace("Subject:", "").strip() or f"Application — {title} | Erman Tagaintchuem"
    body = body.strip()

    if country == "Canada":
        body += CANADA_MOBILITY_NOTE

    today = dt.date.today()
    relance = today + dt.timedelta(days=7)
    can_send = send and not unresolved

    queued_to: Path | None = None
    mailer_result: dict | None = None

    if channel == "email":
        if not recruiter_email:
            raise ApplicationError("recruiter_email est requis pour le canal email")
        if not from_email:
            profile = profile_repository.load_profile(client)
            from_email = profile["personal"]["email"]
        mailer_result = resend_adapter.send(
            to=recruiter_email,
            subject=subject,
            text=body,
            from_email=from_email,
            attachment_path=cv_path,
            dry_run=not can_send,
        )
        sent = not mailer_result["dry_run"]
        statut = "📤 Envoyé" if sent else "🟡 Brouillon (dry-run)"
    else:  # platform — jamais d'auto-envoi, toujours préparé pour validation humaine
        folder_name = f"{today.isoformat()}-{_slugify(company)}-{_slugify(title)}"
        queued_to = queue_repository.enqueue(client, folder_name, subject, body, cv_path)
        sent = False
        statut = "📝 À valider (plateforme)"

    tracker_repository.append_row(
        client,
        {
            "Date": today.isoformat(),
            "Entreprise": company,
            "Poste": title,
            "Pays": country,
            "Type": channel,
            "CV utilisé": role.cv_path or "(aucun)",
            "Contact": recruiter_name or "",
            "Email Recruteur": recruiter_email or "",
            "Statut": statut,
            "Relance le": relance.isoformat() if sent else "",
            "Notes": notes,
        },
    )

    return ApplicationResult(
        role=role,
        match_score=match_score,
        forced_role=forced_role,
        subject=subject,
        body=body,
        unresolved_placeholders=unresolved,
        sent=sent,
        queued_to=queued_to,
        mailer_result=mailer_result,
    )
