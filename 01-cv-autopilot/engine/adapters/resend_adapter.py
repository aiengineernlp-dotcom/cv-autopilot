"""Couche : Adapter.

Fait : seul fichier qui connaît Resend — envoie un email avec pièce jointe.
Interface stable (send()) : remplacer Resend par un autre fournisseur email
= modifier ce seul fichier, rien d'autre dans le produit ne change.
Ne fait jamais : décider si un envoi doit avoir lieu, choisir le destinataire
ou le contenu (Service application_service).
"""
from __future__ import annotations

import base64
import os
from pathlib import Path

import requests

RESEND_ENDPOINT = "https://api.resend.com/emails"


class MailerError(RuntimeError):
    pass


def send(
    *,
    to: str,
    subject: str,
    text: str,
    from_email: str,
    attachment_path: Path | None,
    dry_run: bool,
) -> dict:
    attachments = []
    if attachment_path is not None:
        if not attachment_path.is_file():
            raise MailerError(f"CV introuvable : {attachment_path}")
        content = base64.b64encode(attachment_path.read_bytes()).decode("ascii")
        attachments.append({"filename": attachment_path.name, "content": content})

    payload = {"from": from_email, "to": [to], "subject": subject, "text": text, "attachments": attachments}

    if dry_run:
        return {
            "dry_run": True,
            "payload_preview": {**payload, "attachments": [a["filename"] for a in attachments]},
        }

    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        raise MailerError("RESEND_API_KEY manquant (.env) — impossible d'envoyer réellement.")

    resp = requests.post(
        RESEND_ENDPOINT,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=30,
    )
    if resp.status_code >= 400:
        raise MailerError(f"Resend a refusé l'envoi ({resp.status_code}) : {resp.text}")
    return {"dry_run": False, "resend_response": resp.json()}
