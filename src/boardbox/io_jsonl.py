"""JSON Lines import/export for game events.

Author: Marwan Helmy
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Iterable

from .errors import ExportError, ImportPipelineError, import_pipeline_error
from .game import Game
from .storage import JsonStorage

__author__ = "Marwan Helmy"

EVENT_TYPES = ("game", "meal", "wishlist", "bin", "bins")


def _iter_lines(path: Path) -> Iterable[str]:
    try:
        with path.open(encoding="utf-8") as fh:
            for ln in fh:
                ln = ln.strip()
                if ln:
                    yield ln
    except OSError as exc:
        raise ImportPipelineError("jsonl", str(exc)) from exc


def _load_line(line: str, line_no: int) -> dict[str, Any]:
    try:
        data = json.loads(line)
    except json.JSONDecodeError as exc:
        raise import_pipeline_error("jsonl", line_no, "invalid JSON: %s" % exc) from exc
    if not isinstance(data, dict):
        raise import_pipeline_error("jsonl", line_no, "each line must be a JSON object")
    return data


def export_games_jsonl(storage: JsonStorage, dest: Path) -> int:
    games = storage.list_games(active_only=False)
    try:
        with dest.open("w", encoding="utf-8") as fh:
            for game in games:
                fh.write(json.dumps({"_type": "game", **game.to_dict()}, ensure_ascii=False) + "\n")
        return len(games)
    except OSError as exc:
        raise ExportError("jsonl", str(exc)) from exc


def export_cook_events_jsonl(storage: JsonStorage, dest: Path) -> int:
    events = storage.list_sessions()
    try:
        with dest.open("w", encoding="utf-8") as fh:
            for row in events:
                fh.write(json.dumps({"_type": "meal", **row}, ensure_ascii=False) + "\n")
        return len(events)
    except OSError as exc:
        raise ExportError("jsonl", str(exc)) from exc


def export_events_jsonl(storage: JsonStorage, dest: Path) -> int:
    n = 0
    try:
        with dest.open("w", encoding="utf-8") as fh:
            for game in storage.list_games(active_only=False):
                fh.write(json.dumps({"_type": "game", **game.to_dict()}, ensure_ascii=False) + "\n")
                n += 1
            for row in storage.list_sessions():
                fh.write(json.dumps({"_type": "meal", **row}, ensure_ascii=False) + "\n")
                n += 1
    except OSError as exc:
        raise ExportError("jsonl", str(exc)) from exc
    return n


def export_full_jsonl(storage: JsonStorage, dest: Path) -> int:
    n = 0
    try:
        with dest.open("w", encoding="utf-8") as fh:
            for game in storage.list_games(active_only=False):
                fh.write(json.dumps({"_type": "game", **game.to_dict()}, ensure_ascii=False) + "\n")
                n += 1
            for plan in storage.list_campaigns():
                fh.write(json.dumps({"_type": "night_plan", **plan}, ensure_ascii=False) + "\n")
                n += 1
            for row in storage.list_wishlist():
                fh.write(json.dumps({"_type": "wishlist", **row}, ensure_ascii=False) + "\n")
                n += 1
            for row in storage.list_sessions():
                fh.write(json.dumps({"_type": "meal", **row}, ensure_ascii=False) + "\n")
                n += 1
            for row in storage.list_bin():
                fh.write(json.dumps({"_type": "bin", **row}, ensure_ascii=False) + "\n")
                n += 1
    except OSError as exc:
        raise ExportError("jsonl", str(exc)) from exc
    return n


def import_cook_events_jsonl(storage: JsonStorage, src: Path) -> int:
    if not src.exists():
        raise ImportPipelineError("jsonl", "missing %s" % src)
    n = 0
    for line_no, line in enumerate(_iter_lines(src), start=1):
        data = _load_line(line, line_no)
        kind = data.pop("_type", "meal")
        if kind not in ("meal", "cook"):
            continue
        storage.create_session(data)
        n += 1
    return n


def import_games_jsonl(storage: JsonStorage, src: Path, *, update: bool = False) -> int:
    if not src.exists():
        raise ImportPipelineError("jsonl", "missing %s" % src)
    existing = {r.id: r for r in storage.list_games(active_only=False)}
    n = 0
    for line_no, line in enumerate(_iter_lines(src), start=1):
        data = _load_line(line, line_no)
        kind = data.pop("_type", "game")
        if kind != "game":
            continue
        if not data.get("id"):
            data["id"] = uuid.uuid4().hex[:12]
        game = Game.from_dict(data)
        if game.id in existing:
            if update:
                storage.update_game(game.id, game.to_dict())
            else:
                continue
        else:
            storage.create_game(game)
        existing[game.id] = game
        n += 1
    return n


def import_mixed_jsonl(storage: JsonStorage, src: Path, *, update: bool = False) -> dict[str, int]:
    if not src.exists():
        raise ImportPipelineError("jsonl", "missing %s" % src)
    counts = {k: 0 for k in EVENT_TYPES}
    counts["skipped"] = 0

    for line_no, line in enumerate(_iter_lines(src), start=1):
        data = _load_line(line, line_no)
        kind = data.pop("_type", "game")

        if kind == "game":
            if not data.get("id"):
                data["id"] = uuid.uuid4().hex[:12]
            game = Game.from_dict(data)
            try:
                storage.get_game(game.id)
                if update:
                    storage.update_game(game.id, game.to_dict())
                else:
                    counts["skipped"] += 1
                    continue
            except Exception:
                storage.create_game(game)
            counts["game"] += 1
        elif kind in ("meal", "cook"):
            storage.create_session(data)
            counts["meal"] += 1
        elif kind == "wishlist":
            storage.create_wishlist_item(data)
            counts["wishlist"] += 1
        elif kind in ("bin", "bins"):
            storage.create_bin_item(data)
            counts["bin"] += 1
            counts["bins"] += 1
        elif kind == "night_plan":
            storage.create_campaign(data)
            counts["skipped"] += 1  # counted separately? lump as skipped for now
        else:
            counts["skipped"] += 1

    return counts


export_session_events_jsonl = export_events_jsonl
import_session_events_jsonl = import_cook_events_jsonl
export_cook_events_jsonl = export_events_jsonl
import_cook_events_jsonl = import_cook_events_jsonl
