"""Couche : Service (Logic Engine). Port de ../engine/services/matching_service.py
-- même logique de scoring, adaptée au modèle SQLAlchemy `Role` (Phase 1
utilisait un dataclass distinct de repositories/roles_repository, mais
l'interface (un objet avec `.keywords`) est identique).

Fait : matche le titre et la description d'une offre à la liste des rôles
d'un utilisateur, par score de mots-clés. Le titre pèse 3× plus qu'une
occurrence dans la description. Logique pure, aucun I/O.

Bug déjà corrigé en Phase 1 (2026-08-14), préservé ici : limite de mot
réelle (`\\b...\\b`) au lieu d'un `.count()` naïf -- "geo" ne matche plus
"Geotechnical" mais matche toujours "GEO Specialist".
Ne fait jamais : lire/écrire en base, appeler un LLM ou une API externe.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import Role

TITLE_WEIGHT = 3
DESCRIPTION_WEIGHT = 1


@dataclass
class MatchResult:
    role: "Role | None"
    score: int
    runner_up: list = field(default_factory=list)


def _count_keyword(keyword_low: str, text_low: str) -> int:
    return len(re.findall(rf"\b{re.escape(keyword_low)}\b", text_low))


def _score(role: "Role", title: str, description: str) -> int:
    title_low = title.lower()
    desc_low = description.lower()
    score = 0
    for kw in role.keywords:
        kw_low = kw.lower()
        score += TITLE_WEIGHT * _count_keyword(kw_low, title_low)
        score += DESCRIPTION_WEIGHT * _count_keyword(kw_low, desc_low)
    return score


def match(title: str, description: str, roles: list["Role"]) -> MatchResult:
    if not roles:
        return MatchResult(role=None, score=0, runner_up=[])
    scored = sorted(((r, _score(r, title, description)) for r in roles), key=lambda t: t[1], reverse=True)
    best_role, best_score = scored[0]
    if best_score == 0:
        return MatchResult(role=None, score=0, runner_up=scored[:3])
    return MatchResult(role=best_role, score=best_score, runner_up=scored[1:4])
