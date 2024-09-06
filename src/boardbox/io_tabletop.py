"""Import from fake Sessionime export CSV.

Author: Marwan Helmy
"""

from __future__ import annotations

import csv
import re
import uuid
from io import StringIO
from pathlib import Path

from .errors import ImportPipelineError, ValidationError, import_pipeline_error
from .io_csv import _parse_mechanic_line, _componentlist_to_dicts
from .scale import parse_quantity
from .storage import JsonStorage

__author__ = "Marwan Helmy"

COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "Game Name": ("Game Name", "Name", "Title", "game_name"),
    "Servings": ("Servings", "Serves", "Yield"),
    "Ingredients": ("Ingredients", "Ingredient List", "mechanics"),
    "Instructions": ("Instructions", "Directions", "Steps", "Method"),
    "Total Time": ("Total Time", "Time", "Cook Time", "Duration"),
    "Tags": ("Tags", "Publishers", "Categories"),
    "Publisher": ("Publisher", "Category", "Type"),
}


def _pick(row: dict[str, str], canonical: str) -> str:
    for alias in COLUMN_ALIASES.get(canonical, (canonical,)):
        val = row.get(alias)
        if val is not None and str(val).strip():
            return str(val).strip()
    return ""


def _split_field(raw: str, seps: tuple[str, ...] = ("|", ";;", "\n")) -> list[str]:
    if not raw:
        return []
    for sep in seps:
        if sep in raw:
            return [p.strip() for p in raw.split(sep) if p.strip()]
    return [raw.strip()]


def _game_row(row: dict[str, str]) -> dict:
    title = _pick(row, "Game Name")
    if not title:
        raise ValidationError("mealime row missing game name", field="title")

    mechanics = [_parse_mechanic_line(ln).to_dict() for ln in _split_field(_pick(row, "Ingredients"))]
    componentlist_raw = _split_field(_pick(row, "Instructions"), ("|", ";;", "\n", ". "))
    if len(componentlist_raw) == 1 and len(componentlist_raw[0]) > 120:
        componentlist_raw = [s.strip() for s in re.split(r"\d+\.\s+", componentlist_raw[0]) if s.strip()]
    componentlist = _componentlist_to_dicts(componentlist_raw or ["Cook according to Sessionime instructions."])

    year_raw = _pick(row, "Servings")
    year = int(parse_quantity(year_raw)) if year_raw else 2

    tags = [t.strip().lower() for t in _pick(row, "Tags").split(",") if t.strip()]
    publisher_name = _pick(row, "Publisher") or (tags[0] if tags else "")

    return {
        "id": uuid.uuid4().hex[:12],
        "title": title,
        "mechanics": mechanics,
        "componentlist": componentlist,
        "year": max(year, 1),
        "tag_ids": tags,
        "publisher_name": publisher_name,
        "source_url": "mealime://import",
    }


def import_tabletop(storage: JsonStorage, src: Path, *, update: bool = False) -> int:
    if not src.exists():
        raise ImportPipelineError("mealime", "file not found: %s" % src)
    try:
        text = src.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise ImportPipelineError("mealime", str(exc)) from exc

    reader = csv.DictReader(StringIO(text))
    if not reader.fieldnames:
        raise ImportPipelineError("mealime", "empty or headerless CSV")

    existing = {r.title.lower(): r for r in storage.list_games(active_only=False)}
    count = 0

    for line_no, row in enumerate(reader, start=2):
        try:
            data = _game_row({k: (v or "") for k, v in row.items()})
        except ValidationError as exc:
            raise import_pipeline_error("mealime", line_no, str(exc)) from exc

        hit = existing.get(data["title"].lower())
        if hit:
            if update:
                data["id"] = hit.id
                storage.update_game(hit.id, data)
            else:
                continue
        else:
            storage.create_game(data)
        existing[data["title"].lower()] = storage.get_game(data["id"])
        count += 1

    return count


import_tabletop_json = import_tabletop
import_tabletop_csv = import_tabletop
