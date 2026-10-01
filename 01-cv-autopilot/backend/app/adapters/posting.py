"""Couche : Adapter (type partagé). Copie de ../engine/adapters/posting.py
(duplication délibérée -- voir cv_style.py pour le même raisonnement).

Fait : définit la forme normalisée d'une offre récupérée par n'importe quel
Adapter de découverte (Greenhouse, Lever, futurs Gmail/IMAP) -- permet au
Service de traiter toutes les sources de la même façon.
Ne fait jamais : savoir comment récupérer une offre.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Posting:
    source: str  # "greenhouse" | "lever" | ...
    external_id: str
    company: str
    title: str
    location: str
    url: str
    description: str
