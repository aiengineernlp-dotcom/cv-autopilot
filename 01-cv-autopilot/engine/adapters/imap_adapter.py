"""Couche : Adapter.

Fait : seul fichier qui connaît le protocole IMAP — se connecte en lecture
seule (`readonly=True`, aucune commande d'écriture/suppression n'est même
utilisée) à une boîte mail hébergée n'importe où (pas seulement Gmail —
c'est tout l'intérêt : un hébergeur web, Zoho, Microsoft 365...), et
récupère les emails correspondant à une recherche par expéditeur. Rend le
contenu brut ; ne l'interprète pas.
Ne fait jamais : décider quels emails chercher ou comment en extraire des
offres (Service), écrire/supprimer un email.

Setup : voir GUIDE_UTILISATION_PHASE1.md. Nécessite host/port/utilisateur
(data-<client>/imap_accounts.json — pas secret) et un mot de passe (.env,
jamais commis, variable IMAP_PASSWORD_<LABEL_MAJUSCULE>) — utiliser un mot
de passe d'application si l'hébergeur le permet, jamais le mot de passe
principal du compte si évitable.
"""
from __future__ import annotations

import email as email_lib
import imaplib
from email.header import decode_header


class ImapError(RuntimeError):
    pass


def _decode_header_value(value) -> str:
    if not value:
        return ""
    decoded = ""
    for text, enc in decode_header(value):
        decoded += text.decode(enc or "utf-8", errors="replace") if isinstance(text, bytes) else text
    return decoded


def _extract_body(msg: email_lib.message.Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            disp = str(part.get("Content-Disposition") or "")
            if part.get_content_type() in ("text/plain", "text/html") and "attachment" not in disp:
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode(part.get_content_charset() or "utf-8", errors="replace")
        return ""
    payload = msg.get_payload(decode=True)
    if not payload:
        return ""
    return payload.decode(msg.get_content_charset() or "utf-8", errors="replace")


def search_messages(
    sender_contains: str,
    *,
    host: str,
    port: int,
    username: str,
    password: str,
    max_results: int = 20,
) -> list[dict]:
    """Retourne une liste de messages bruts : {id, subject, from, date, body_text}."""
    try:
        conn = imaplib.IMAP4_SSL(host, port, timeout=15)
        conn.login(username, password)
    except (imaplib.IMAP4.error, OSError, TimeoutError) as e:
        raise ImapError(f"Connexion IMAP échouée ({host}:{port}, {username}) : {e}") from e

    try:
        conn.select("INBOX", readonly=True)
        status, data = conn.search(None, f'(FROM "{sender_contains}")')
        if status != "OK":
            raise ImapError(f"Recherche IMAP échouée : {status}")

        message_ids = data[0].split()[-max_results:]  # les plus récents

        messages = []
        for msg_id in reversed(message_ids):
            status, msg_data = conn.fetch(msg_id, "(RFC822)")
            if status != "OK" or not msg_data or not msg_data[0]:
                continue
            msg = email_lib.message_from_bytes(msg_data[0][1])
            messages.append({
                "id": msg_id.decode(),
                "subject": _decode_header_value(msg.get("Subject")),
                "from": _decode_header_value(msg.get("From")),
                "date": msg.get("Date", ""),
                "body_text": _extract_body(msg),
            })
        return messages
    finally:
        conn.logout()
