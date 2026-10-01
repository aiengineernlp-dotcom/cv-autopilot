"""Couche : Service -- génère le .docx final d'un rôle. Port de
../engine/services/cv_generation_service.py (Phase 1, même structure de
document, même ordre de sections) adapté au modèle relationnel de la
Phase 2 : `job_1`/`job_2` fixes deviennent une boucle sur les expériences
liées au rôle (`role_experience_bullets`), "un seul projet" devient une
boucle sur `role_projects` (plusieurs projets possibles, contrairement à
la Phase 1).
Ne fait jamais : connaître le détail du format .docx (délègue à cv_style),
requête SQL directe (délègue aux Repositories)."""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from .. import cv_style
from ..core import storage
from ..repositories import cv_file_repository, role_repository, user_repository


class CvGenerationError(RuntimeError):
    """Erreur métier (rôle introuvable, profil incomplet...) -- jamais une exception technique brute."""


def _contact_lines(user_email: str, profile) -> tuple[str, str]:
    parts_1 = [user_email, profile.phone, profile.linkedin_url, profile.github_url]
    contact_line_1 = "  |  ".join(p for p in parts_1 if p)

    parts_2 = [profile.location, profile.portfolio_url]
    contact_line_2 = "  |  ".join(p for p in parts_2 if p)

    return contact_line_1, contact_line_2


async def generate(db: AsyncSession, *, user_id: uuid.UUID, role_id: uuid.UUID) -> tuple[str, int]:
    role = await role_repository.get_role(db, role_id=role_id, user_id=user_id)
    if role is None:
        raise CvGenerationError("Rôle introuvable")

    user = await user_repository.get_by_id(db, user_id)
    profile = await user_repository.get_profile(db, user_id)
    experience_bullets = await role_repository.list_role_experience_bullets(db, role_id)
    projects = await role_repository.list_role_projects(db, role_id)

    doc = cv_style.new_document()

    cv_style.add_name(doc, user.full_name)
    cv_style.add_title(doc, role.name)
    contact_line_1, contact_line_2 = _contact_lines(user.email, profile)
    cv_style.add_contact_line(doc, contact_line_1, color=cv_style.GRAY, space_after=1.75)
    if contact_line_2:
        cv_style.add_contact_line(doc, contact_line_2, color=cv_style.LIGHT_GRAY, space_after=7.0)

    if role.summary:
        cv_style.add_section_header(doc, "PROFESSIONAL SUMMARY")
        cv_style.add_body_paragraph(doc, role.summary)

    if experience_bullets:
        cv_style.add_section_header(doc, "WORK EXPERIENCE")
        for experience, bullet_row in experience_bullets:
            cv_style.add_entry_header(doc, experience.position_title, experience.company_location, experience.date_range)
            for b in bullet_row.bullets:
                cv_style.add_bullet(doc, b)

    if projects:
        cv_style.add_section_header(doc, "KEY PROJECTS" if len(projects) > 1 else "KEY PROJECT")
        for project in projects:
            cv_style.add_entry_header(doc, project.title, project.subtitle or "", project.year or "")
            for b in project.bullets:
                cv_style.add_bullet(doc, b)

    if profile.education:
        cv_style.add_section_header(doc, "EDUCATION")
        for edu in profile.education:
            cv_style.add_entry_header(doc, edu.get("degree", ""), edu.get("institution", ""), edu.get("date", ""))

    if role.skills:
        cv_style.add_section_header(doc, "TECHNICAL SKILLS")
        for entry in role.skills:
            items = entry.get("items", [])
            cv_style.add_skill_line(doc, entry.get("category", ""), ", ".join(items) if isinstance(items, list) else str(items))

    if profile.certifications:
        cv_style.add_section_header(doc, "CERTIFICATIONS & TRAINING")
        for cert in profile.certifications:
            label = cert.get("name", "")
            if cert.get("status"):
                label += f" — {cert['status']}"
            cv_style.add_bullet(doc, label)

    previous = await cv_file_repository.get_latest(db, role_id)
    version = (previous.version if previous else 0) + 1

    storage_key = storage.save_generated_docx(user_id, role_id, version, doc)
    await cv_file_repository.create(db, role_id=role_id, storage_key=storage_key, version=version)
    await role_repository.mark_cv_ready(db, role)

    return storage_key, version
