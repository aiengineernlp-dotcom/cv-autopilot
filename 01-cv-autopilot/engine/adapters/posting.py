"""Couche : Adapter (type partagé).

Fait : définit la forme normalisée d'une offre récupérée par n'importe quel
Adapter de découverte (Greenhouse, Lever, futurs autres) — permet au Service
de traiter toutes les sources de la même façon, sans connaître leurs API respectives.
Ne fait jamais : savoir comment récupérer une offre — ça, c'est le rôle de
chaque Adapter concret.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Posting:
    source: str          # "greenhouse" | "lever" | ...
    external_id: str
    company: str
    title: str
    location: str
    url: str
    description: str
