"""Couche : Repository.

Fait : seul fichier autorisé à lire/écrire data-<client>/tracker-candidatures.md —
ajoute une ligne à la table markdown, la relit, met à jour une ligne précise après
une relance, et expose le template de relance déjà présent dans ce même fichier.
Ne fait jamais : décider du statut, de la date de relance, ou si une relance doit
partir (Services application_service / followup_service).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ..config import ClientConfig

COLUMNS = [
    "Date", "Entreprise", "Poste", "Pays", "Type", "CV utilisé",
    "Contact", "Email Recruteur", "Statut", "Relance le", "Notes",
]
HEADER_MARK = "| " + " | ".join(COLUMNS) + " |"
RELANCE_BLOCK_RE = re.compile(r"## Template de relance.*?\n```\n(.*?)\n```", re.S)


@dataclass
class TrackerRow:
    line_index: int  # position dans le fichier — sert à update_row()
    values: dict


def _path(client: ClientConfig) -> Path:
    return client.root / "tracker-candidatures.md"


def _table_bounds(lines: list[str]) -> tuple[int, int]:
    header_idx = next(i for i, l in enumerate(lines) if l.strip() == HEADER_MARK)
    sep_idx = header_idx + 1
    end_idx = sep_idx + 1
    while end_idx < len(lines) and lines[end_idx].strip().startswith("|"):
        end_idx += 1
    return sep_idx, end_idx


def append_row(client: ClientConfig, row: dict) -> None:
    path = _path(client)
    lines = path.read_text(encoding="utf-8").splitlines()
    sep_idx, end_idx = _table_bounds(lines)

    block = lines[sep_idx + 1:end_idx]
    block = [l for l in block if l.replace("|", "").strip() != ""]  # retire lignes vides du template
    block.append("| " + " | ".join(row.get(c, "") for c in COLUMNS) + " |")

    lines[sep_idx + 1:end_idx] = block
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def list_rows(client: ClientConfig) -> list[TrackerRow]:
    lines = _path(client).read_text(encoding="utf-8").splitlines()
    sep_idx, end_idx = _table_bounds(lines)

    rows = []
    for i in range(sep_idx + 1, end_idx):
        line = lines[i]
        if line.replace("|", "").strip() == "":
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != len(COLUMNS):
            continue  # ligne malformée — ignorée plutôt que de planter
        rows.append(TrackerRow(line_index=i, values=dict(zip(COLUMNS, cells))))
    return rows


def update_row(client: ClientConfig, line_index: int, changes: dict) -> None:
    path = _path(client)
    lines = path.read_text(encoding="utf-8").splitlines()
    cells = [c.strip() for c in lines[line_index].strip().strip("|").split("|")]
    values = dict(zip(COLUMNS, cells))
    values.update(changes)
    lines[line_index] = "| " + " | ".join(values.get(c, "") for c in COLUMNS) + " |"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_followup_template(client: ClientConfig) -> str:
    text = _path(client).read_text(encoding="utf-8")
    m = RELANCE_BLOCK_RE.search(text)
    if not m:
        raise ValueError("Template de relance introuvable dans tracker-candidatures.md")
    return m.group(1).strip()
