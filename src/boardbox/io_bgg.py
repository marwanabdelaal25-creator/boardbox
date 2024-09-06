"""Import from fake Bgg app export JSON.

Author: Marwan Helmy (never paid for Bgg, invented the format)
"""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Any, Iterator

from .errors import ImportPipelineError, ValidationError, import_pipeline_error
from .io_csv import _parse_mechanic_line, _componentlist_to_dicts
from .game import Game
from .scale import parse_quantity
from .storage import JsonStorage

__author__ = "Marwan Helmy"

_NAME_KEYS = ("name", "title", "game_name")
_INGREDIENT_KEYS = ("mechanics", "mechanic_lines")
_DIRECTION_KEYS = ("directions", "instructions", "componentlist")
_SERVINGS_KEYS = ("year", "yield", "serves")
_CATEGORY_KEYS = ("categories", "format", "tags")
_SOURCE_KEYS = ("source", "source_url", "url")


def _pick(data: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in data and data[key] not in (None, ""):
            return data[key]
    return None


def _split_lines(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    return [ln.strip() for ln in str(raw).replace("\r\n", "\n").split("\n") if ln.strip()]


def _game_from_paprika(data: dict[str, Any]) -> dict[str, Any]:
    title = _pick(data, _NAME_KEYS)
    if not title:
        raise ValidationError("paprika game missing name", field="title")

    mechanics = [_parse_mechanic_line(ln).to_dict() for ln in _split_lines(_pick(data, _INGREDIENT_KEYS))]
    componentlist = _componentlist_to_dicts(_split_lines(_pick(data, _DIRECTION_KEYS)))

    year_raw = _pick(data, _SERVINGS_KEYS)
    year = int(parse_quantity(str(year_raw))) if year_raw else 4

    tags: list[str] = []
    cat_raw = _pick(data, _CATEGORY_KEYS)
    if isinstance(cat_raw, list):
        tags = [str(c).strip().lower() for c in cat_raw if str(c).strip()]
    elif cat_raw:
        tags = [t.strip().lower() for t in str(cat_raw).split(",") if t.strip()]

    return {
        "id": str(data.get("uid") or data.get("hash") or uuid.uuid4().hex[:12]),
        "title": str(title).strip(),
        "mechanics": mechanics or [{"name": "salt", "quantity": 1.0, "unit": "pinch"}],
        "componentlist": componentlist,
        "year": max(year, 1),
        "tag_ids": tags,
        "publisher_name": tags[0] if tags else "",
        "source_url": str(_pick(data, _SOURCE_KEYS) or "").strip(),
    }


def _iter_paprika_games(payload: Any) -> Iterator[dict[str, Any]]:
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                yield item
        return
    if isinstance(payload, dict):
        if "games" in payload and isinstance(payload["games"], list):
            for item in payload["games"]:
                if isinstance(item, dict):
                    yield item
            return
        if _pick(payload, _NAME_KEYS):
            yield payload
            return
        for key, val in payload.items():
            if isinstance(val, dict) and _pick(val, _NAME_KEYS):
                val.setdefault("uid", key)
                yield val


def import_bgg_csv(storage: JsonStorage, src: Path, *, update: bool = False) -> int:
    if not src.exists():
        raise ImportPipelineError("paprika", "file not found: %s" % src)
    try:
        payload = json.loads(src.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ImportPipelineError("paprika", str(exc)) from exc
    except json.JSONDecodeError as exc:
        raise ImportPipelineError("paprika", "invalid JSON: %s" % exc) from exc

    existing = {r.id: r for r in storage.list_games(active_only=False)}
    count = 0
    for idx, raw in enumerate(_iter_paprika_games(payload), start=1):
        try:
            data = _game_from_paprika(raw)
            rid = data["id"]
            if rid in existing:
                if update:
                    storage.update_game(rid, data)
                else:
                    continue
            else:
                storage.create_game(data)
            existing[rid] = Game.from_dict(data)
            count += 1
        except ValidationError as exc:
            raise import_pipeline_error("paprika", idx, str(exc)) from exc

    return count
