"""CSV import/export for games and wishlist lists.

Author: Marwan Helmy — spreadsheet escape hatch for meal prep Sundays.
"""

from __future__ import annotations

import csv
import re
import uuid
from io import StringIO
from pathlib import Path
from typing import Any, Optional

from .errors import ExportError, ImportPipelineError, ValidationError, import_pipeline_error
from .game import Game, MechanicStub, MechanicStep
from .scale import parse_quantity
from .storage import JsonStorage

__author__ = "Marwan Helmy"

RECIPE_FIELDS = [
    "id",
    "title",
    "year",
    "publisher_name",
    "format",
    "tag_ids",
    "source_url",
    "mechanics",
    "componentlist",
]

SHOPPING_FIELDS = [
    "name",
    "quantity",
    "unit",
    "aisle",
    "checked",
    "list_id",
    "source_games",
]


def _read_csv_text(path: Path) -> str:
    if not path.exists():
        raise ImportPipelineError("csv", "file not found: %s" % path)
    try:
        return path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise ImportPipelineError("csv", str(exc)) from exc


def _join_list(items: list[str], sep: str = " | ") -> str:
    return sep.join(items)


def _split_list(raw: Optional[str], sep: str = " | ") -> list[str]:
    if not raw:
        return []
    return [p.strip() for p in raw.split(sep) if p.strip()]


def _encode_mechanics(game: Game) -> str:
    parts = []
    for ing in game.mechanics:
        unit = ing.unit.strip()
        if unit:
            parts.append("%s %s %s" % (ing.quantity, unit, ing.name))
        else:
            parts.append("%s %s" % (ing.quantity, ing.name))
    return _join_list(parts, " ;; ")


def _parse_mechanic_line(line: str) -> MechanicStub:
    line = line.strip()
    optional = bool(re.search(r"\(optional\)", line, re.I))
    clean = re.sub(r"\(optional\)", "", line, flags=re.I).strip()
    m = re.match(r"^([\d./\s]+)\s+(\S+)\s+(.+)$", clean)
    if m:
        qty = parse_quantity(m.group(1).strip())
        unit = m.group(2)
        name = m.group(3)
        return MechanicStub(name=name.strip(), quantity=qty, unit=unit, notes="optional" if optional else "")
    m2 = re.match(r"^([\d./]+)\s+(.+)$", clean)
    if m2:
        return MechanicStub(name=m2.group(2).strip(), quantity=parse_quantity(m2.group(1)), notes="optional" if optional else "")
    return MechanicStub(name=clean, quantity=1.0, notes="optional" if optional else "")


def _componentlist_to_dicts(componentlist: list[str]) -> list[dict[str, Any]]:
    out = []
    for i, text in enumerate(componentlist, start=1):
        if text.strip():
            out.append(MechanicStep(order=i, text=text.strip()).to_dict())
    return out or [MechanicStep(order=1, text="Combine and cook.").to_dict()]


def export_games_csv(storage: JsonStorage, dest: Path) -> int:
    try:
        with dest.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=RECIPE_FIELDS)
            writer.writeheader()
            count = 0
            for game in storage.list_games(active_only=False):
                writer.writerow({
                    "id": game.id,
                    "title": game.title,
                    "year": game.year,
                    "publisher_name": game.publisher_name,
                    "format": game.format,
                    "tag_ids": ", ".join(game.tag_ids),
                    "source_url": game.source_url,
                    "mechanics": _encode_mechanics(game),
                    "componentlist": _join_list(game.step_texts()),
                })
                count += 1
        return count
    except OSError as exc:
        raise ExportError("csv", str(exc)) from exc


def export_wishlist_csv(storage: JsonStorage, dest: Path, list_id: Optional[str] = None) -> int:
    items = storage.list_wishlist(list_id=list_id)
    try:
        with dest.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=SHOPPING_FIELDS)
            writer.writeheader()
            count = 0
            for row in items:
                writer.writerow({
                    "name": row.get("name", ""),
                    "quantity": row.get("quantity", ""),
                    "unit": row.get("unit", ""),
                    "aisle": row.get("aisle", "other"),
                    "checked": "yes" if row.get("checked") else "no",
                    "list_id": row.get("list_id", ""),
                    "source_games": ", ".join(row.get("source_games", [])),
                })
                count += 1
        return count
    except OSError as exc:
        raise ExportError("csv", str(exc)) from exc


def import_games_csv(
    storage: JsonStorage,
    src: Path,
    *,
    update: bool = False,
) -> int:
    text = _read_csv_text(src)
    reader = csv.DictReader(StringIO(text))
    if not reader.fieldnames or "title" not in reader.fieldnames:
        raise ImportPipelineError("csv", "missing required column: title")

    existing = {r.id: r for r in storage.list_games(active_only=False)}
    by_title = {r.title.lower(): r for r in existing.values()}
    count = 0

    for line_no, row in enumerate(reader, start=2):
        title = (row.get("title") or "").strip()
        if not title:
            continue
        rid = (row.get("id") or "").strip()
        hit: Game | None = None
        if rid and rid in existing:
            hit = existing[rid]
        elif update:
            hit = by_title.get(title.lower())

        try:
            componentlist = _split_list(row.get("componentlist"))
            if not componentlist and row.get("componentlist"):
                componentlist = [row["componentlist"].strip()]
            mechanics = [_parse_mechanic_line(ln) for ln in _split_list(row.get("mechanics") or "", " ;; ")]
            if not mechanics and row.get("mechanics"):
                mechanics = [_parse_mechanic_line(row["mechanics"])]
            data: dict[str, Any] = {
                "id": hit.id if hit else (rid or uuid.uuid4().hex[:12]),
                "title": title,
                "componentlist": _componentlist_to_dicts(componentlist),
                "mechanics": [i.to_dict() for i in mechanics] or [{"name": "salt", "quantity": 1.0, "unit": "pinch"}],
                "year": int(row.get("year") or 4),
                "publisher_name": (row.get("publisher_name") or "").strip(),
                "format": (row.get("format") or "").strip(),
                "tag_ids": [t.strip() for t in (row.get("tag_ids") or row.get("tags") or "").split(",") if t.strip()],
                "source_url": (row.get("source_url") or "").strip(),
            }
            if hit is None:
                created = storage.create_game(data)
                existing[created.id] = created
                by_title[created.title.lower()] = created
            else:
                updated = storage.update_game(hit.id, data)
                existing[updated.id] = updated
            count += 1
        except (ValidationError, ValueError) as exc:
            raise import_pipeline_error("csv", line_no, str(exc)) from exc

    return count


def import_wishlist_csv(storage: JsonStorage, src: Path, *, list_id: str = "imported") -> int:
    text = _read_csv_text(src)
    reader = csv.DictReader(StringIO(text))
    if not reader.fieldnames or "name" not in reader.fieldnames:
        raise ImportPipelineError("csv", "missing required column: name")

    count = 0
    for line_no, row in enumerate(reader, start=2):
        item_name = (row.get("name") or "").strip()
        if not item_name:
            continue
        try:
            qty = parse_quantity(row.get("quantity") or "1")
            checked = (row.get("checked") or "").strip().lower() in ("1", "yes", "y", "true")
            sources = [s.strip() for s in (row.get("source_games") or "").split(",") if s.strip()]
            storage.create_wishlist_item({
                "name": item_name,
                "quantity": qty,
                "unit": (row.get("unit") or "").strip(),
                "aisle": (row.get("aisle") or "other").strip(),
                "checked": checked,
                "list_id": (row.get("list_id") or list_id).strip(),
                "source_games": sources,
            })
            count += 1
        except ValueError as exc:
            raise import_pipeline_error("csv", line_no, str(exc)) from exc

    return count
