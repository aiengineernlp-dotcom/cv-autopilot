"""Couche : Adapter -- seul fichier qui connaît le protocole SMTP. Envoie un
email avec pièce jointe depuis la propre boîte mail de l'utilisateur (2026-08-16,
décision produit : contrairement à Phase 1 CLI qui envoie via Resend depuis
un domaine unique, le canal email web envoie depuis les identifiants SMTP
réels de chaque utilisateur -- plus fidèle à "candidater soi-même", plus
crédible pour le recruteur qui reçoit l'email).
Ne fait jamais : décider si un envoi doit avoir lieu, choisir le destinataire
ou le contenu (Service), déchiffrer un mot de passe (reçoit toujours le mot
de passe déjà en clair, déchiffré par l'appelant)."""
from __future__ import annotations

import smtplib
from email import utils
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path


class SmtpError(RuntimeError):
    pass


def send(
    *,
    host: str,
    port: int,
    username: str,
    password: str,
    from_email: str,
    to: str,
    subject: str,
    text: str,
    attachment_path: Path | None,
    dry_run: bool,
) -> dict:
    """dry_run=True (le défaut partout où cet Adapter est appelé pour l'instant,
    2026-08-16) : construit le message, vérifie que la pièce jointe existe,
    mais n'ouvre aucune connexion SMTP -- même principe que Resend en Phase 1
    (jamais d'envoi réel sans un geste explicite et déjà vérifié par
    l'utilisateur)."""
    if attachment_path is not None and not attachment_path.is_file():
        raise SmtpError(f"CV introuvable : {attachment_path}")

    if dry_run:
        return {
            "dry_run": True,
            "preview": {
                "from": from_email, "to": to, "subject": subject, "text": text,
                "attachment": attachment_path.name if attachment_path else None,
            },
        }

    msg = MIMEMultipart()
    msg["From"] = from_email
    msg["To"] = to
    msg["Subject"] = subject
    msg["Date"] = utils.formatdate(localtime=True)
    msg["Message-ID"] = utils.make_msgid()
    # Trouvé en testant en réel (2026-08-16) : sans ces deux headers, le message
    # part sans Date ni Message-ID -- absence classique qui dégrade le score
    # anti-spam ; email.mime ne les ajoute jamais automatiquement.
    msg.attach(MIMEText(text, "plain"))

    if attachment_path is not None:
        part = MIMEApplication(attachment_path.read_bytes(), Name=attachment_path.name)
        part["Content-Disposition"] = f'attachment; filename="{attachment_path.name}"'
        msg.attach(part)

    try:
        # SMTP_SSL directement (port 465, le plus courant) -- pas de STARTTLS
        # séparé pour rester simple ; à revoir si un hébergeur exige le 587.
        with smtplib.SMTP_SSL(host, port, timeout=15) as conn:
            conn.login(username, password)
            conn.sendmail(from_email, [to], msg.as_string())
    except (smtplib.SMTPException, OSError, TimeoutError) as e:
        raise SmtpError(f"Envoi SMTP échoué ({host}:{port}, {username}) : {e}") from e

    return {"dry_run": False}
