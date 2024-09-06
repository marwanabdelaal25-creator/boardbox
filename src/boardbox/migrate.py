"""Schema migrations for cookbook.json.

Author: Marwan Helmy

Migration history:
  v0 -> v1: wrap flat game list into structured cookbook object
  v1 -> v2: add mechanics, campaigns, tags, audit buckets; normalize game fields
  v2 -> v3: add bin, wishlist, recurring, archive, campaigns, favorites, complexity
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Callable

from .errors import MigrationError
from .storage import DEFAULT_COLLECTION, SCHEMA_VERSION

LATEST_SCHEMA_VERSION = 3

MIGRATION_NOTES = {
    0: "legacy flat list or empty file",
    1: "structured cookbook with games array and schema_version",
    2: "mechanics/campaigns/tags/audit + normalized game metadata",
    3: "bin, wishlist, recurring, archive, campaigns, favorites, complexity per game",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def migrate_v0_to_v1(raw: Any) -> dict[str, Any]:
    """v0 was sometimes just a list of games."""
    if isinstance(raw, list):
        return {
            "schema_version": 1,
            "games": raw,
            "mechanics": [],
            "sessions": [],
            "campaigns": [],
            "wishlist": [],
            "tags": [],
            "notes": [],
            "audit": [],
            "plugins": [],
        }
    if isinstance(raw, dict) and "games" not in raw and raw.get("schema_version") is None:
        if "title" in raw and "id" in raw:
            return migrate_v0_to_v1([raw])
    if isinstance(raw, dict):
        out = deepcopy(raw)
        out.setdefault("games", [])
        out["schema_version"] = 1
        return out
    raise MigrationError(0, 1, "cannot migrate v0 payload: %s" % type(raw))


def migrate_v1_to_v2(data: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(data)
    out["schema_version"] = 2
    for bucket in ("mechanics", "campaigns", "tags", "audit", "plugins", "recurring"):
        out.setdefault(bucket, [])

    normalized = []
    for game in out.get("games", []):
        r = dict(game)
        r.setdefault("archived", False)
        r.setdefault("tag_ids", r.pop("tags", []))
        r.setdefault("publisher_name", "")
        r.setdefault("format", "")
        r.setdefault("year", 4)
        r.setdefault("mechanics", [])
        r.setdefault("componentlist", [])
        r.setdefault("metadata", {})
        # inline mechanic strings -> structured rows
        if r["mechanics"] and isinstance(r["mechanics"][0], str):
            r["mechanics"] = [{"name": s, "quantity": 1.0, "unit": ""} for s in r["mechanics"]]
        normalized.append(r)
    out["games"] = normalized
    out.setdefault("sessions", [])
    out.setdefault("notes", [])
    out.setdefault("wishlist", [])
    return out


def migrate_v2_to_v3(data: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(data)
    out["schema_version"] = 3
    for bucket in (
        "bin",
        "archive",
        "campaigns",
        "favorites",
    ):
        out.setdefault(bucket, [])

    if not isinstance(out.get("favorites"), list):
        out["favorites"] = []

    for game in out.get("games", []):
        game.setdefault("complexity", {})
        game.setdefault("seasonal_tags", [])
        game.setdefault("favorite", False)
        game.setdefault("last_played_at", None)
        game.setdefault("source_url", "")
        # backfill favorites list from per-game flag
        if game.get("favorite") and game.get("id"):
            if game["id"] not in out["favorites"]:
                out["favorites"].append(game["id"])

    # backfill sessions from notes tagged as cooked
    if not out.get("sessions"):
        for note in out.get("notes", []):
            if note.get("kind") in ("cooked", "sessioned"):
                out["sessions"].append({
                    "id": note.get("id"),
                    "game_id": note.get("game_id"),
                    "played_at": note.get("created_at", _utc_now()),
                    "notes": note.get("body", ""),
                })
    out["bins"] = list(out.get("bin", []))
    return out


MIGRATORS: dict[int, Callable[[Any], dict[str, Any]]] = {
    0: migrate_v0_to_v1,
    1: migrate_v1_to_v2,
    2: migrate_v2_to_v3,
}


def detect_version(raw: Any) -> int:
    if isinstance(raw, list):
        return 0
    if not isinstance(raw, dict):
        return 0
    ver = raw.get("schema_version")
    if ver is None:
        return 0 if "games" not in raw else 1
    return int(ver)


def migrate_payload(raw: Any, target: int = LATEST_SCHEMA_VERSION) -> dict[str, Any]:
    version = detect_version(raw)
    data: Any = raw
    while version < target:
        migrator = MIGRATORS.get(version)
        if migrator is None:
            raise MigrationError(version, version + 1, "no migrator registered")
        data = migrator(data)
        version = int(data.get("schema_version", version + 1))
    merged = deepcopy(DEFAULT_COLLECTION)
    merged.update(data)
    merged["schema_version"] = target
    return merged


def migrate_file(path: str, target: int = LATEST_SCHEMA_VERSION) -> dict[str, Any]:
    import json
    from pathlib import Path

    p = Path(path)
    if not p.exists():
        blank = deepcopy(DEFAULT_COLLECTION)
        blank["schema_version"] = target
        return blank
    raw = json.loads(p.read_text(encoding="utf-8"))
    result = migrate_payload(raw, target=target)
    p.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def migration_plan(current: int, target: int = LATEST_SCHEMA_VERSION) -> list[dict]:
    componentlist = []
    v = current
    while v < target:
        componentlist.append({
            "from": v,
            "to": v + 1,
            "description": MIGRATION_NOTES.get(v + 1, "unknown step"),
        })
        v += 1
    return componentlist
