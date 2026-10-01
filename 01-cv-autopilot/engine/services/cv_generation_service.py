"""Couche : Service — orchestrateur.

Fait : construit un CV .docx à partir du profil (Repository profile_repository) et du
contenu par rôle (Repository cv_content_repository) — tous deux propres au client —
en utilisant les primitives de présentation (cv_style — Presentation, générique,
ne connaît aucun rôle ni domaine métier), l'enregistre au bon endroit dans le
dossier client, puis met à jour roles.json via roles_repository.
Ne fait jamais : connaître le détail du format .docx (délègue à cv_style), lire/écrire
un fichier lui-même (délègue toujours au Repository concerné), contenir du texte en
dur propre à un client — tout vient de cv_content.json.
"""
from __future__ import annotations

from pathlib import Path

from .. import cv_style
from ..config import ClientConfig
from ..repositories import cv_content_repository, profile_repository, roles_repository


class CvGenerationError(RuntimeError):
    pass


def generate(client: ClientConfig, role_id: str) -> Path:
    content = cv_content_repository.load(client)
    data = content["roles"].get(role_id)
    if data is None:
        raise CvGenerationError(f"Pas de contenu défini pour '{role_id}' dans data-{client.client_id}/cv_content.json")

    profile = profile_repository.load_profile(client)
    full_name = profile["personal"]["fullName"]

    doc = cv_style.new_document()

    cv_style.add_name(doc, full_name)
    cv_style.add_title(doc, data["title"])
    cv_style.add_contact_line(doc, content["contact_line_1"], color=cv_style.GRAY, space_after=1.75)
    cv_style.add_contact_line(doc, content["contact_line_2"], color=cv_style.LIGHT_GRAY, space_after=7.0)

    cv_style.add_section_header(doc, "PROFESSIONAL SUMMARY")
    cv_style.add_body_paragraph(doc, data["summary"])

    cv_style.add_section_header(doc, "WORK EXPERIENCE")
    cv_style.add_entry_header(doc, *content["job_1"])
    for b in data["job1_bullets"]:
        cv_style.add_bullet(doc, b)
    cv_style.add_entry_header(doc, *content["job_2"])
    for b in data["job2_bullets"]:
        cv_style.add_bullet(doc, b)

    cv_style.add_section_header(doc, "KEY PROJECT")
    cv_style.add_entry_header(doc, data["project_title"], data["project_sub"], data["project_year"])
    for b in data["project_bullets"]:
        cv_style.add_bullet(doc, b)

    cv_style.add_section_header(doc, "EDUCATION")
    cv_style.add_entry_header(doc, *content["education"])

    cv_style.add_section_header(doc, "TECHNICAL SKILLS")
    for category, items in data["skills"]:
        cv_style.add_skill_line(doc, category, items)

    cv_style.add_section_header(doc, "CERTIFICATIONS & TRAINING")
    for cert in content["certifications"]:
        cv_style.add_bullet(doc, cert)

    relative_path = f"{data['target_dir']}/{data['filename']}"
    out_path = client.root / relative_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out_path)

    roles_repository.mark_cv_generated(
        client, role_id, relative_path, notes=data.get("post_generation_note", "CV généré.")
    )
    return out_path
