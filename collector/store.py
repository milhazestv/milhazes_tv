"""Persistencia do dataset canonico.

Append-only. Um registo que ja existe nunca e reescrito, apenas o campo
`first_seen` original e preservado. O historico do git passa assim a ser
a trilha de auditoria: qualquer alteracao retroactiva a numeros antigos
aparece no diff.
"""

from __future__ import annotations

import json
from pathlib import Path

from .models import Appearance, DATA_DIR

APPEARANCES = DATA_DIR / "appearances.json"
QUARANTINE = DATA_DIR / "quarantine.json"


def load(path: Path = APPEARANCES) -> dict[str, dict]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {row["id"]: row for row in payload.get("appearances", [])}


def merge(existing: dict[str, dict], incoming: list[Appearance]) -> tuple[dict, int, int]:
    added = 0
    updated = 0
    for appearance in incoming:
        row = appearance.to_dict()
        current = existing.get(row["id"])
        if current is None:
            existing[row["id"]] = row
            added += 1
            continue
        row["first_seen"] = current.get("first_seen", row["first_seen"])
        if row != current:
            existing[row["id"]] = row
            updated += 1
    return existing, added, updated


def save(rows: dict[str, dict], path: Path = APPEARANCES) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(rows.values(), key=lambda r: (r["date"], r["id"]))
    payload = {"schema": 1, "count": len(ordered), "appearances": ordered}
    # sort_keys e indent fixos para que o diff do git seja legivel.
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def save_quarantine(entries: list[dict], path: Path = QUARANTINE) -> None:
    """Itens rejeitados pela recolha, com o motivo. Nada desaparece em
    silêncio — quem quiser auditar as exclusões tem aqui a lista completa
    desta corrida."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": 1,
        "count": len(entries),
        "entries": sorted(entries, key=lambda e: (e["source"], e["date"])),
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )
