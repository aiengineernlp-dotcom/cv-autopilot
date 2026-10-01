"""Miroir Python des types ENUM Postgres définis dans docs/schema.sql.
Garder synchronisé à la main -- schema.sql reste la source de vérité DDL,
ces enums sont la vue typée côté application."""
from __future__ import annotations

import enum


class ChannelType(str, enum.Enum):
    email = "email"
    platform = "platform"


class ApplicationStatus(str, enum.Enum):
    """Vocabulaire repris tel quel de tracker-candidatures.md (Phase 1) --
    voir docs/schema.sql pour la correspondance emoji -> valeur."""

    queued = "queued"
    sent = "sent"
    viewed = "viewed"
    contacted = "contacted"
    interview_scheduled = "interview_scheduled"
    offer_received = "offer_received"
    rejected = "rejected"
    follow_up_sent = "follow_up_sent"
    waiting = "waiting"


class SourceType(str, enum.Enum):
    ats_greenhouse = "ats_greenhouse"
    ats_lever = "ats_lever"
    gmail = "gmail"
    imap = "imap"


class SourceStatus(str, enum.Enum):
    active = "active"
    error = "error"
    disabled = "disabled"


class ExtractionStatus(str, enum.Enum):
    pending_review = "pending_review"
    confirmed = "confirmed"
    discarded = "discarded"


class CvUploadStatus(str, enum.Enum):
    uploaded = "uploaded"
    extracting = "extracting"
    extracted = "extracted"
    failed = "failed"
