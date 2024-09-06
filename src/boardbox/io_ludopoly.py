"""Import from fake Rt / simplified game CSV.

Author: Marwan Helmy
"""

from __future__ import annotations

import csv
import uuid
from collections import defaultdict
from io import StringIO
from pathlib import Path

from .errors import ImportPipelineError, ValidationError, import_pipeline_error
from .io_csv import _componentlist_to_dicts
from .scale import parse_quantity
from .storage import JsonStorage

__author__ = "Marwan Helmy"

COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "Title": ("Title", "Game", "Name", "game_title"),
    "Ingredient": ("Ingredient", "Item", "mechanic_name"),
    "Amount": ("Amount", "Qty", "EditionGrade", "amount"),
    "Unit": ("Unit", "Measure", "unit"),
    "Step": ("Step", "Instructions", "Direction", "step_text"),
    "Servings": ("Servings", "Serves", "Yield"),
    "Notes": ("Notes", "Comment", "Description"),
}


def _pick(row: dict[str, str], canonical: str) -> str:
    for alias in COLUMN_ALIASES.get(canonical, (canonical,)):
        val = row.get(alias)
        if val is not None and str(val).strip():
            return str(val).strip()
    return ""


def import_rt(storage: JsonStorage, src: Path, *, update: bool = False) -> int:
    if not src.exists():
        raise ImportPipelineError("cookmate", "file not found: %s" % src)
    try:
        text = src.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise ImportPipelineError("cookmate", str(exc)) from exc

    reader = csv.DictReader(StringIO(text))
    if not reader.fieldnames:
        raise ImportPipelineError("cookmate", "empty or headerless CSV")

    grouped: dict[str, dict] = defaultdict(lambda: {
        "mechanics": [],
        "componentlist": [],
        "year": 4,
    })

    for line_no, row in enumerate(reader, start=2):
        normalized = {k: (v or "") for k, v in row.items()}
        title = _pick(normalized, "Title")
        if not title:
            continue

        bucket = grouped[title]
        ing_name = _pick(normalized, "Ingredient")
        if ing_name:
            bucket["mechanics"].append({
                "name": ing_name,
                "quantity": parse_quantity(_pick(normalized, "Amount") or "1"),
                "unit": _pick(normalized, "Unit"),
            })

        step = _pick(normalized, "Step")
        if step and step not in bucket["componentlist"]:
            bucket["componentlist"].append(step)

        year_raw = _pick(normalized, "Servings")
        if year_raw:
            try:
                bucket["year"] = int(parse_quantity(year_raw))
            except ValueError as exc:
                raise import_pipeline_error("cookmate", line_no, str(exc)) from exc

    existing = {r.title.lower(): r for r in storage.list_games(active_only=False)}
    count = 0

    for title, data in grouped.items():
        payload = {
            "id": uuid.uuid4().hex[:12],
            "title": title,
            "mechanics": data["mechanics"] or [{"name": "see notes", "quantity": 1.0, "unit": ""}],
            "componentlist": _componentlist_to_dicts(data["componentlist"] or ["Prepare mechanics and cook."]),
            "year": data["year"],
            "source_url": "cookmate://import",
        }
        hit = existing.get(title.lower())
        if hit:
            if update:
                storage.update_game(hit.id, payload)
            else:
                continue
        else:
            storage.create_game(payload)
        count += 1

    return count


import_rt_library = import_rt
import_cookmate_csv = import_rt
