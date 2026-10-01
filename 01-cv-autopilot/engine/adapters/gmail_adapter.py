"""Couche : Adapter.

Fait : seul fichier qui connaît l'API Gmail — authentifie en lecture seule
(OAuth, scope `gmail.readonly`) et récupère les emails correspondant à une
recherche (ex : alertes LinkedIn/Indeed). Rend le contenu brut ; ne
l'interprète pas. Supporte plusieurs comptes Gmail — un jeton par compte,
le même fichier `client_secret_gmail.json` (projet Google Cloud) sert pour
tous.
Ne fait jamais : décider quels emails chercher ou comment en extraire des
offres (Service), écrire/supprimer un email — le scope lecture seule ne le
permettrait de toute façon pas.

Setup : voir GUIDE_UTILISATION_PHASE1.md, section alertes email. Chaque
nouveau compte doit d'abord être ajouté comme "testeur" dans l'écran de
consentement OAuth (Google Cloud Console) avant sa première autorisation
ici. Premier appel pour un compte donné = ouverture d'un navigateur pour
autoriser l'accès (fichier `client_secret_gmail.json`, jamais commis) —
ensuite, le jeton de ce compte (`gmail_token_<compte>.json`, jamais commis
non plus) est réutilisé automatiquement.
"""
from __future__ import annotations

import base64
import re
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
PRODUCT_ROOT = Path(__file__).resolve().parent.parent.parent
CREDENTIALS_PATH = PRODUCT_ROOT / "client_secret_gmail.json"

_SLUG_RE = re.compile(r"[^a-zA-Z0-9]+")


class GmailAuthError(RuntimeError):
    pass


def _token_path(account: str) -> Path:
    slug = _SLUG_RE.sub("_", account).strip("_")
    return PRODUCT_ROOT / f"gmail_token_{slug}.json"


def _get_credentials(account: str) -> Credentials:
    token_path = _token_path(account)
    creds = None
    if token_path.is_file():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_PATH.is_file():
                raise GmailAuthError(
                    f"Fichier d'identifiants introuvable : {CREDENTIALS_PATH}. "
                    "Télécharge-le depuis Google Cloud Console (voir GUIDE_UTILISATION_PHASE1.md)."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
            print(f"Autorisation pour {account} — le navigateur va s'ouvrir. "
                  f"Connecte-toi avec CE compte précisément.")
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json(), encoding="utf-8")
        token_path.chmod(0o600)

    return creds


def _extract_body(payload: dict) -> str:
    """Extrait le texte (brut ou HTML) d'un message Gmail — structure MIME imbriquée."""
    if payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")

    for part in payload.get("parts", []) or []:
        if part.get("mimeType") in ("text/plain", "text/html"):
            data = part.get("body", {}).get("data")
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
        if part.get("parts"):
            nested = _extract_body(part)
            if nested:
                return nested
    return ""


def search_messages(query: str, account: str, max_results: int = 20) -> list[dict]:
    """Retourne une liste de messages bruts : {id, subject, from, date, body_text}."""
    creds = _get_credentials(account)
    # static_discovery=False : force la récupération en ligne de la définition
    # de l'API plutôt que la copie locale embarquée dans la librairie, qui
    # posait problème (UnknownApiNameOrVersion) dans cet environnement.
    service = build("gmail", "v1", credentials=creds, static_discovery=False)

    result = service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
    message_ids = result.get("messages", [])

    messages = []
    for m in message_ids:
        msg = service.users().messages().get(userId="me", id=m["id"], format="full").execute()
        headers = {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}
        messages.append({
            "id": m["id"],
            "subject": headers.get("Subject", ""),
            "from": headers.get("From", ""),
            "date": headers.get("Date", ""),
            "body_text": _extract_body(msg["payload"]),
        })
    return messages
