"""Couche : Repository -- seul fichier autorisé à faire une requête SQL sur
`experiences`/`roles`/`role_experience_bullets`/`role_projects`."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Experience, Role, RoleExperienceBullet, RoleProject


async def list_experiences(db: AsyncSession, user_id: uuid.UUID) -> list[Experience]:
    result = await db.execute(select(Experience).where(Experience.user_id == user_id).order_by(Experience.sort_order))
    return list(result.scalars().all())


async def sync_experiences(db: AsyncSession, user_id: uuid.UUID, experiences: list[dict]) -> list[Experience]:
    """Met à jour les expériences de l'utilisateur avec la liste fournie
    (venant du draft confirmé) -- appelé à chaque confirmation, y compris
    une reconfirmation après un premier rôle déjà créé.

    Ancienne version (`replace_experiences`) supprimait puis recréait toutes
    les lignes -- `role_experience_bullets.experience_id` a ON DELETE CASCADE,
    donc reconfirmer après avoir créé un rôle effaçait silencieusement ses
    bullets. Corrigé le 2026-08-15 (trouvé avant qu'un utilisateur ne le
    déclenche, en construisant la réinitialisation de profil) : les
    expériences existantes (même poste + même entreprise) sont mises à jour
    sur place, jamais supprimées -- l'identité de la ligne (et donc les
    bullets qui en dépendent) survit. Seules les expériences réellement
    nouvelles sont ajoutées."""
    existing = {(e.position_title, e.company_location): e for e in await list_experiences(db, user_id)}
    rows: list[Experience] = []

    for i, exp in enumerate(experiences):
        key = (exp["position_title"], exp["company_location"])
        row = existing.get(key)
        if row is not None:
            row.date_range = exp["date_range"]
            row.sort_order = i
        else:
            row = Experience(
                user_id=user_id,
                position_title=exp["position_title"],
                company_location=exp["company_location"],
                date_range=exp["date_range"],
                sort_order=i,
            )
            db.add(row)
        rows.append(row)

    await db.commit()
    for row in rows:
        await db.refresh(row)
    return rows


async def create_role(
    db: AsyncSession, *, user_id: uuid.UUID, name: str, summary: str | None, skills: list, keywords: list,
) -> Role:
    # status="draft" : le contenu (adaptation + mots-clés) existe, mais pas
    # encore de .docx -- cv_generation_service passe à "cv_ready" une fois
    # le fichier réellement généré (voir cv_generation_service.generate()).
    role = Role(user_id=user_id, name=name, summary=summary, skills=skills, keywords=keywords, status="draft")
    db.add(role)
    await db.commit()
    await db.refresh(role)
    return role


async def get_role(db: AsyncSession, *, role_id: uuid.UUID, user_id: uuid.UUID) -> Role | None:
    result = await db.execute(select(Role).where(Role.id == role_id, Role.user_id == user_id))
    return result.scalar_one_or_none()


async def list_role_experience_bullets(db: AsyncSession, role_id: uuid.UUID) -> list[tuple[Experience, RoleExperienceBullet]]:
    result = await db.execute(
        select(Experience, RoleExperienceBullet)
        .join(RoleExperienceBullet, RoleExperienceBullet.experience_id == Experience.id)
        .where(RoleExperienceBullet.role_id == role_id)
        .order_by(RoleExperienceBullet.sort_order)
    )
    return [(exp, bullet) for exp, bullet in result.all()]


async def list_role_projects(db: AsyncSession, role_id: uuid.UUID) -> list[RoleProject]:
    result = await db.execute(select(RoleProject).where(RoleProject.role_id == role_id).order_by(RoleProject.sort_order))
    return list(result.scalars().all())


async def mark_cv_ready(db: AsyncSession, role: Role) -> None:
    role.status = "cv_ready"
    await db.commit()


async def delete_role(db: AsyncSession, role: Role) -> None:
    """CASCADE côté schéma supprime déjà role_experience_bullets/role_projects/
    cv_files liés -- le Service appelant doit avoir déjà effacé les fichiers
    physiques des cv_files avant d'appeler ceci (voir onboarding_service.delete_role)."""
    await db.delete(role)
    await db.commit()


async def add_experience_bullets(db: AsyncSession, *, role_id: uuid.UUID, experience_id: uuid.UUID, bullets: list, sort_order: int) -> None:
    db.add(RoleExperienceBullet(role_id=role_id, experience_id=experience_id, bullets=bullets, sort_order=sort_order))
    await db.commit()


async def add_role_project(db: AsyncSession, *, role_id: uuid.UUID, title: str, subtitle: str | None, year: str | None, bullets: list, sort_order: int) -> None:
    db.add(RoleProject(role_id=role_id, title=title, subtitle=subtitle, year=year, bullets=bullets, sort_order=sort_order))
    await db.commit()


async def list_roles(db: AsyncSession, user_id: uuid.UUID) -> list[Role]:
    result = await db.execute(select(Role).where(Role.user_id == user_id).order_by(Role.created_at))
    return list(result.scalars().all())


async def name_exists(db: AsyncSession, *, user_id: uuid.UUID, name: str) -> bool:
    """Utilisé pour désambiguïser automatiquement un nom de rôle avant
    création (2026-08-15, voir onboarding_service.create_role_from_posting)
    -- `roles` a une contrainte UNIQUE(user_id, name) ; sans ce contrôle,
    coller deux fois la même offre (même titre + même entreprise) plantait
    en 500 brut au lieu d'un comportement géré."""
    result = await db.execute(select(Role.id).where(Role.user_id == user_id, Role.name == name))
    return result.scalar_one_or_none() is not None
