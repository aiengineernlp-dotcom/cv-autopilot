"""Couche : Service -- porté tel quel de ../../../engine/services/email_alert_service.py
(2026-08-16, brique 1 de l'auto-envoi email portée au web -- voir discovery_service.py
pour le point d'entrée qui l'appelle). Copie déclarée, pas réutilisée par
import direct -- `backend/` doit rester déployable seul (voir cv_style.py
pour le même raisonnement).

Fait : parse le texte brut d'une alerte email (Indeed ou LinkedIn — déjà
récupéré par l'Adapter gmail_adapter ou imap_adapter) et en extrait chaque
offre individuelle sous forme de Posting — la même forme normalisée que les
Adapters ATS (Greenhouse, Lever), pour que le reste du pipeline (matching,
application_service) n'ait pas à savoir d'où vient une offre. Logique pure
sur du texte déjà en mémoire.
Ne fait jamais : appeler l'API Gmail/IMAP (Adapters), décider si une offre
correspond au profil (Service matching_service).

Format Indeed observé (2026-08-14) — un bloc par offre, séparés par une
ligne vide :
    Titre du poste
    Entreprise - Lieu
    [Fourchette de salaire — optionnel]
    [Easily apply — optionnel]
    Description (1 ligne, tronquée par "…")
    Il y a X jours / Just posted
    https://lien-vers-loffre

Format LinkedIn observé (2026-08-14, trouvé dans une boîte IMAP tierce —
aucune alerte LinkedIn n'existait sur les comptes Gmail testés) — un bloc
par offre, séparés par une ligne de tirets ; pas de description :
    Titre du poste
    Entreprise
    Lieu
    [badges optionnels — "N connection(s)", "This company is actively
     hiring", "Apply with resume & profile"...]
    View job: https://www.linkedin.com/comm/jobs/view/<id>/?trackingId=...

Le pied de page (désinscription, mentions légales...) est ignoré
automatiquement dans les deux formats.
"""
from __future__ import annotations

import hashlib
import re
from urllib.parse import parse_qs, urlparse

from ..adapters.posting import Posting

TIME_RE = re.compile(r"^(Just posted|Today|\d+\+? days? ago|\d+\+? hours? ago)$", re.IGNORECASE)
URL_RE = re.compile(r"^https?://\S+$")
NOISE_LINES = {"Easily apply", "Urgently hiring", "New"}

LINKEDIN_VIEW_JOB_RE = re.compile(r"^View job:\s*(https?://\S+)\s*$", re.MULTILINE)
LINKEDIN_JOB_ID_RE = re.compile(r"/jobs/view/(\d+)/")
LINKEDIN_HEADER_PREFIXES = ("manage alerts", "your job alert")


def _stable_id(url: str, company: str, title: str) -> str:
    """Le paramètre 'jk' (job key) d'Indeed identifie une offre organique de façon
    stable — contrairement au reste de l'URL, qui change à chaque email envoyé
    pour la même offre (tracking). Les annonces sponsorisées ('pagead') n'ont pas
    de 'jk' du tout, et leur paramètre 'ad' change lui aussi à chaque email —
    repli sur un hash (entreprise + titre) dans ce cas : moins précis qu'un vrai
    identifiant (deux offres différentes avec le même intitulé chez la même
    entreprise seraient confondues), mais bien plus fiable que l'URL, qui
    garantissait un doublon à chaque nouvelle réception de la même annonce."""
    jk = parse_qs(urlparse(url).query).get("jk")
    if jk:
        return jk[0]
    return "adhash:" + hashlib.sha1(f"{company}|{title}".lower().encode("utf-8")).hexdigest()[:16]


def _split_blocks(body_text: str) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] = []
    for raw_line in body_text.splitlines():
        line = raw_line.strip()
        if line == "":
            if current:
                blocks.append(current)
                current = []
        else:
            current.append(line)
    if current:
        blocks.append(current)
    return blocks


def parse_indeed_alert(body_text: str) -> list[Posting]:
    postings: list[Posting] = []

    for block in _split_blocks(body_text):
        if len(block) < 4:
            continue
        if not URL_RE.match(block[-1]):
            continue
        if not TIME_RE.match(block[-2]):
            continue

        title = block[0]
        company_location = block[1]
        if " - " in company_location:
            company, location = company_location.split(" - ", 1)
        else:
            company, location = company_location, ""

        middle = [l for l in block[2:-2] if l not in NOISE_LINES]
        description = " ".join(middle)

        company_clean, title_clean = company.strip(), title.strip()
        postings.append(Posting(
            source="indeed_alert",
            external_id=_stable_id(block[-1], company_clean, title_clean),
            company=company_clean,
            title=title_clean,
            location=location.strip(),
            url=block[-1],
            description=description,
        ))

    return postings


def parse_linkedin_alert(body_text: str) -> list[Posting]:
    """LinkedIn ne fournit pas de description dans l'email (contrairement à
    Indeed) — le matching pour ces offres repose entièrement sur le titre."""
    text = body_text.replace("\r\n", "\n")
    postings: list[Posting] = []
    prev_end = 0

    for m in LINKEDIN_VIEW_JOB_RE.finditer(text):
        chunk = text[prev_end:m.start()]
        prev_end = m.end()

        lines = [l.strip() for l in chunk.splitlines() if l.strip()]
        lines = [
            l for l in lines
            if not l.lower().startswith(LINKEDIN_HEADER_PREFIXES)
            and "match your preferences" not in l.lower()
            and not l.startswith("---")
        ]
        if len(lines) < 3:
            continue

        title, company, location = lines[0], lines[1], lines[2]

        # Bruit trouvé en testant sur de vrais emails (2026-08-14) : les sections
        # "New jobs from your other alerts" / "See all jobs on LinkedIn" / "Edit
        # alert" n'ont pas la forme titre/entreprise/lieu — une URL complète se
        # glisse dans un des 3 champs. Sans ce filtre, un mot-clé présent dans
        # l'URL elle-même (ex: "seo" dans "?keywords=web+and+seo+python") peut
        # matcher un rôle par erreur — vécu en réel : "SEO / GEO Specialist"
        # matché sur une URL de recherche, pas un vrai poste.
        if any("http" in f.lower() for f in (title, company, location)):
            continue
        if title.lower().startswith(("see all jobs", "edit alert", "new jobs from")):
            continue

        url = m.group(1)
        job_id = LINKEDIN_JOB_ID_RE.search(url)

        postings.append(Posting(
            source="linkedin_alert",
            external_id=job_id.group(1) if job_id else url,
            company=company,
            title=title,
            location=location,
            url=url,
            description="",
        ))

    return postings
