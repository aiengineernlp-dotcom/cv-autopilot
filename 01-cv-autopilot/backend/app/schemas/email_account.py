"""Couche : schémas (contrat HTTP, Pydantic) -- comptes email."""
from __future__ import annotations

import datetime as dt
import uuid

from pydantic import BaseModel


class ConnectEmailAccountRequest(BaseModel):
    label: str
    imap_host: str
    imap_port: int = 993
    smtp_host: str
    smtp_port: int = 465
    username: str
    password: str  # jamais persisté en clair -- voir email_account_service.connect


class EmailAccountOut(BaseModel):
    """Ne renvoie JAMAIS encrypted_password -- même chiffré, aucune raison
    qu'il quitte le serveur."""

    id: uuid.UUID
    label: str
    imap_host: str
    imap_port: int
    smtp_host: str
    smtp_port: int
    username: str
    created_at: dt.datetime

    model_config = {"from_attributes": True}
