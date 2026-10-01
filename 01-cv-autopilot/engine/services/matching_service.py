"""Couche : Service (Logic Engine).

Fait : matche le titre et la description d'une offre à la liste des rôles déjà
chargés, par score de mots-clés. Le titre pèse 3× plus qu'une occurrence dans
la description — un mot-clé dans le titre est un signal fort ("Data Analyst"),
le même mot noyé dans le texte "qui sommes-nous" générique d'une entreprise
(ex : "...des startups les plus ambitieuses...") ne veut souvent rien dire du
poste réel. Logique pure sur des objets en mémoire.
Ne fait jamais : lire ou écrire un fichier (Repository roles_repository), appeler
un LLM ou un email — aucune dépendance externe, aucun I/O.

Phase 1 : scoring par mots-clés. Conçu pour être remplacé plus tard par un matching
sémantique (embeddings / Claude API) sans changer l'appelant : match(title, description, roles).

Bug trouvé et corrigé le 2026-08-14 : un mot-clé court ("geo") matchait comme simple
sous-chaîne à l'intérieur d'un mot sans rapport ("Geotechnical Engineer" a matché
SEO/GEO Specialist). Le score utilise maintenant une vraie limite de mot (\\b...\\b) —
"geo" ne matche plus "Geotechnical", mais matche toujours "SEO/GEO" ou "GEO Specialist".
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..repositories.roles_repository import Role

TITLE_WEIGHT = 3
DESCRIPTION_WEIGHT = 1


@dataclass
class MatchResult:
    role: Role | None
    score: int
    runner_up: list = field(default_factory=list)  # [(role, score), ...]


def _count_keyword(keyword_low: str, text_low: str) -> int:
    return len(re.findall(rf"\b{re.escape(keyword_low)}\b", text_low))


def _score(role: Role, title: str, description: str) -> int:
    title_low = title.lower()
    desc_low = description.lower()
    score = 0
    for kw in role.keywords:
        kw_low = kw.lower()
        score += TITLE_WEIGHT * _count_keyword(kw_low, title_low)
        score += DESCRIPTION_WEIGHT * _count_keyword(kw_low, desc_low)
    return score


def match(title: str, description: str, roles: list[Role]) -> MatchResult:
    scored = sorted(((r, _score(r, title, description)) for r in roles), key=lambda t: t[1], reverse=True)
    best_role, best_score = scored[0]
    if best_score == 0:
        return MatchResult(role=None, score=0, runner_up=scored[:3])
    return MatchResult(role=best_role, score=best_score, runner_up=scored[1:4])
