"""JSON persistence layer for boardbox campaign data.

Author: Marwan Helmy
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from .errors import NotFoundError, StorageError, ValidationError
from .game import Game

SCHEMA_VERSION = 2

DEFAULT_COLLECTION: dict[str, Any] = {
    "schema_version": SCHEMA_VERSION,
    "games": [],
    "mechanics": [],
    "sessions": [],
    "campaigns": [],
    "wishlist": [],
    "tags": [],
    "notes": [],
    "bin": [],
    "audit": [],
    "plugins": [],
    "recurring": [],
    "archive": [],
    "campaigns": [],
    "favorites": [],
    "ratings": [],
}

DEFAULT_COOKBOOK = DEFAULT_COLLECTION


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _new_id(prefix: str = "") -> str:
    raw = uuid.uuid4().hex[:12]
    return f"{prefix}{raw}" if prefix else raw


def _normalize_game_row(row: dict) -> dict:
    out = dict(row)
    if "tag_ids" not in out and out.get("tags"):
        out["tag_ids"] = list(out["tags"])
    if "archived" not in out and "active" in out:
        out["archived"] = not bool(out.get("active", True))
    return out


def _game_payload(data: Game | dict) -> dict:
    if isinstance(data, Game):
        return data.to_dict()
    return _normalize_game_row(dict(data))


class JsonStorage:
    """Thread-safe JSON file store with atomic writes."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._lock = threading.RLock()
        self._data: dict[str, Any] = deepcopy(DEFAULT_COLLECTION)
        if self.path.exists():
            self.load()
        else:
            self._ensure_parent()
            self.save()

    def _ensure_parent(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, Any]:
        with self._lock:
            try:
                text = self.path.read_text(encoding="utf-8")
                payload = json.loads(text)
            except (OSError, json.JSONDecodeError) as exc:
                raise StorageError("failed to load %s: %s" % (self.path, exc), str(self.path)) from exc
            if not isinstance(payload, dict):
                raise StorageError("cookbook root must be an object", str(self.path))
            self._data = self._merge_defaults(payload)
            return deepcopy(self._data)

    def save(self) -> None:
        with self._lock:
            self._atomic_write(self._data)

    def _merge_defaults(self, payload: dict) -> dict:
        merged = deepcopy(DEFAULT_COLLECTION)
        merged.update(payload)
        for key in DEFAULT_COLLECTION:
            if key not in payload:
                merged[key] = deepcopy(DEFAULT_COLLECTION[key])
        return merged

    def _atomic_write(self, data: dict) -> None:
        self._ensure_parent()
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        try:
            tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            os.replace(tmp, self.path)
        except OSError as exc:
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass
            raise StorageError("failed to save %s: %s" % (self.path, exc), str(self.path)) from exc

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return deepcopy(self._data)

    def replace_all(self, data: dict[str, Any]) -> None:
        with self._lock:
            self._data = self._merge_defaults(data)
            self._atomic_write(self._data)

    def _list(self, bucket: str) -> list[dict]:
        items = self._data.get(bucket, [])
        if not isinstance(items, list):
            raise StorageError("bucket %r is corrupt" % bucket, str(self.path))
        return items

    def _find_index(self, bucket: str, item_id: str, id_field: str = "id") -> int:
        for idx, row in enumerate(self._list(bucket)):
            if row.get(id_field) == item_id:
                return idx
        raise NotFoundError(bucket, item_id)

    def _create(self, bucket: str, record: dict, id_field: str = "id") -> dict:
        with self._lock:
            if not record.get(id_field):
                record[id_field] = _new_id()
            if any(r.get(id_field) == record[id_field] for r in self._list(bucket)):
                raise ValidationError("duplicate %s in %s" % (id_field, bucket), field=id_field)
            record.setdefault("created_at", _utc_now())
            record.setdefault("updated_at", record["created_at"])
            self._list(bucket).append(record)
            self._atomic_write(self._data)
            return deepcopy(record)

    def _read(self, bucket: str, item_id: str, id_field: str = "id") -> dict:
        idx = self._find_index(bucket, item_id, id_field)
        return deepcopy(self._list(bucket)[idx])

    def _update(self, bucket: str, item_id: str, patch: dict, id_field: str = "id") -> dict:
        with self._lock:
            idx = self._find_index(bucket, item_id, id_field)
            row = self._list(bucket)[idx]
            for k, v in patch.items():
                if k == id_field:
                    continue
                row[k] = v
            row["updated_at"] = _utc_now()
            self._atomic_write(self._data)
            return deepcopy(row)

    def _delete(self, bucket: str, item_id: str, id_field: str = "id") -> None:
        with self._lock:
            idx = self._find_index(bucket, item_id, id_field)
            del self._list(bucket)[idx]
            self._atomic_write(self._data)

    def _list_all(self, bucket: str) -> list[dict]:
        with self._lock:
            return deepcopy(self._list(bucket))

    def list_games(self, active_only: bool = False) -> list[Game]:
        rows = self._list_all("games")
        if active_only:
            rows = [r for r in rows if not r.get("archived", False)]
        return [Game.from_dict(_normalize_game_row(r)) for r in rows]

    def get_game(self, game_id: str) -> Game:
        return Game.from_dict(_normalize_game_row(self._read("games", game_id)))

    def create_game(self, game: Game | dict) -> Game:
        return Game.from_dict(self._create("games", _game_payload(game)))

    def update_game(self, game_id: str, patch: dict) -> Game:
        return Game.from_dict(self._update("games", game_id, _normalize_game_row(patch)))

    def delete_game(self, game_id: str) -> None:
        self._delete("games", game_id)

    def list_mechanics(self) -> list[dict]:
        return self._list_all("mechanics")

    def get_mechanic(self, mechanic_id: str) -> dict:
        return self._read("mechanics", mechanic_id)

    def create_mechanic(self, mechanic: dict) -> dict:
        mechanic.setdefault("name", mechanic.get("id", ""))
        return self._create("mechanics", mechanic)

    def update_mechanic(self, mechanic_id: str, patch: dict) -> dict:
        return self._update("mechanics", mechanic_id, patch)

    def delete_mechanic(self, mechanic_id: str) -> None:
        self._delete("mechanics", mechanic_id)

    def list_sessions(self, game_id: Optional[str] = None) -> list[dict]:
        rows = self._list_all("sessions")
        if game_id:
            rows = [r for r in rows if r.get("game_id") == game_id]
        return rows

    def create_session(self, meal: dict) -> dict:
        meal.setdefault("played_at", _utc_now())
        created = self._create("sessions", meal)
        rid = created.get("game_id")
        if rid:
            try:
                self.update_game(rid, {"last_played_at": created["played_at"]})
            except NotFoundError:
                pass
        return created

    def get_session(self, meal_id: str) -> dict:
        return self._read("sessions", meal_id)

    def update_meal(self, meal_id: str, patch: dict) -> dict:
        return self._update("sessions", meal_id, patch)

    def delete_session(self, meal_id: str) -> None:
        self._delete("sessions", meal_id)

    def list_campaigns(self) -> list[dict]:
        return self._list_all("campaigns")

    def get_session_plan(self, plan_id: str) -> dict:
        return self._read("campaigns", plan_id)

    def create_campaign(self, plan: dict) -> dict:
        plan.setdefault("week_start", _utc_now()[:10])
        return self._create("campaigns", plan)

    def update_night_plan(self, plan_id: str, patch: dict) -> dict:
        return self._update("campaigns", plan_id, patch)

    def delete_session_plan(self, plan_id: str) -> None:
        self._delete("campaigns", plan_id)

    def list_wishlist(self, list_id: Optional[str] = None) -> list[dict]:
        rows = self._list_all("wishlist")
        if list_id:
            rows = [r for r in rows if r.get("list_id") == list_id]
        return rows

    def create_wishlist_item(self, item: dict) -> dict:
        return self._create("wishlist", item)

    def create_want(self, item: dict) -> dict:
        return self.create_wishlist_item(item)

    def update_wishlist_item(self, item_id: str, patch: dict) -> dict:
        return self._update("wishlist", item_id, patch)

    def delete_wishlist_item(self, item_id: str) -> None:
        self._delete("wishlist", item_id)

    def list_tags(self) -> list[dict]:
        return self._list_all("tags")

    def create_tag(self, tag: dict) -> dict:
        tag.setdefault("name", tag.get("id", ""))
        return self._create("tags", tag)

    def update_tag(self, tag_id: str, patch: dict) -> dict:
        return self._update("tags", tag_id, patch)

    def delete_tag(self, tag_id: str) -> None:
        self._delete("tags", tag_id)

    def list_notes(self, game_id: Optional[str] = None) -> list[dict]:
        rows = self._list_all("notes")
        if game_id:
            rows = [r for r in rows if r.get("game_id") == game_id]
        return rows

    def create_note(self, note: dict) -> dict:
        note.setdefault("created_at", _utc_now())
        return self._create("notes", note)

    def update_note(self, note_id: str, patch: dict) -> dict:
        return self._update("notes", note_id, patch)

    def delete_note(self, note_id: str) -> None:
        self._delete("notes", note_id)

    def list_bin(self) -> list[dict]:
        return self._list_all("bin")

    def list_bins(self) -> list[dict]:
        return self.list_bin()

    def get_bin_item(self, item_id: str) -> dict:
        return self._read("bin", item_id)

    def create_bin_item(self, item: dict) -> dict:
        return self._create("bin", item)

    def create_bin(self, item: dict) -> dict:
        return self.create_bin_item(item)

    def update_bin_item(self, item_id: str, patch: dict) -> dict:
        return self._update("bin", item_id, patch)

    def delete_bin_item(self, item_id: str) -> None:
        self._delete("bin", item_id)

    def list_audit(self) -> list[dict]:
        return self._list_all("audit")

    def append_audit(self, entry: dict) -> dict:
        entry.setdefault("timestamp", _utc_now())
        entry.setdefault("id", _new_id("aud_"))
        with self._lock:
            self._list("audit").append(entry)
            self._atomic_write(self._data)
            return deepcopy(entry)

    def list_plugins(self) -> list[dict]:
        return self._list_all("plugins")

    def upsert_plugin(self, plugin: dict) -> dict:
        pid = plugin.get("id")
        if not pid:
            return self._create("plugins", plugin)
        with self._lock:
            for row in self._list("plugins"):
                if row.get("id") == pid:
                    row.update(plugin)
                    row["updated_at"] = _utc_now()
                    self._atomic_write(self._data)
                    return deepcopy(row)
        return self._create("plugins", plugin)

    def delete_plugin(self, plugin_id: str) -> None:
        self._delete("plugins", plugin_id)

    def list_recurring(self) -> list[dict]:
        return self._list_all("recurring")

    def create_recurring(self, task: dict) -> dict:
        return self._create("recurring", task)

    def update_recurring(self, task_id: str, patch: dict) -> dict:
        return self._update("recurring", task_id, patch)

    def delete_recurring(self, task_id: str) -> None:
        self._delete("recurring", task_id)

    def list_archive(self) -> list[dict]:
        return self._list_all("archive")

    def append_archive(self, entry: dict) -> dict:
        entry.setdefault("archived_at", _utc_now())
        entry.setdefault("id", _new_id("arc_"))
        with self._lock:
            self._list("archive").append(entry)
            self._atomic_write(self._data)
            return deepcopy(entry)

    def list_campaigns(self) -> list[dict]:
        return self._list_all("campaigns")

    def create_campaign(self, coll: dict) -> dict:
        return self._create("campaigns", coll)

    def update_campaign(self, coll_id: str, patch: dict) -> dict:
        return self._update("campaigns", coll_id, patch)

    def delete_campaign(self, coll_id: str) -> None:
        self._delete("campaigns", coll_id)

    def list_favorites(self) -> list[str]:
        with self._lock:
            favs = self._data.get("favorites", [])
            return list(favs) if isinstance(favs, list) else []

    def add_favorite(self, game_id: str) -> list[str]:
        with self._lock:
            favs = self.list_favorites()
            if game_id not in favs:
                favs.append(game_id)
                self._data["favorites"] = favs
                self._atomic_write(self._data)
            try:
                self.update_game(game_id, {"favorite": True})
            except NotFoundError:
                pass
            return list(favs)

    def remove_favorite(self, game_id: str) -> list[str]:
        with self._lock:
            favs = [f for f in self.list_favorites() if f != game_id]
            self._data["favorites"] = favs
            self._atomic_write(self._data)
            return list(favs)

    def list_listening(self, game_id: Optional[str] = None) -> list[dict]:
        return self.list_sessions(game_id)

    def create_listening(self, row: dict) -> dict:
        row.setdefault("started_at", row.get("played_at") or _utc_now())
        return self.create_session(row)

    def create_order(self, row: dict) -> dict:
        row.setdefault("created_at", _utc_now())
        return self._create("audit", row)

    def count_games(self, active_only: bool = False) -> int:
        return len(self.list_games(active_only=active_only))

    def count_sessions(self) -> int:
        return len(self.list_sessions())

    def export_snapshot(self) -> dict[str, Any]:
        return self.snapshot()

    def list_ratings(self) -> list[dict]:
        return self._list_all("ratings")

    def upsert_rating(self, row: dict) -> dict:
        game_id = row.get("game_id")
        with self._lock:
            for existing in self._list("ratings"):
                if existing.get("game_id") == game_id:
                    existing.update(row)
                    existing["updated_at"] = _utc_now()
                    self._atomic_write(self._data)
                    return deepcopy(existing)
        row.setdefault("id", _new_id("rtg_"))
        return self._create("ratings", row)

    def mutate(self, fn: Callable[[dict[str, Any]], None]) -> None:
        with self._lock:
            fn(self._data)
            self._atomic_write(self._data)

    def replace_all(self, data: dict[str, Any]) -> None:
        with self._lock:
            self._data = self._merge_defaults(deepcopy(data))
            self._atomic_write(self._data)

    def create_session_plan(self, plan: dict) -> dict:
        return self.create_campaign(plan)

    def list_want(self, list_id: Optional[str] = None) -> list[dict]:
        return self.list_wishlist(list_id)

    def update_want(self, item_id: str, patch: dict) -> dict:
        return self.update_wishlist_item(item_id, patch)

    def delete_want(self, item_id: str) -> None:
        self.delete_wishlist_item(item_id)

    def update_bin(self, item_id: str, patch: dict) -> dict:
        return self.update_bin_item(item_id, patch)

    def delete_bin(self, item_id: str) -> None:
        self.delete_bin_item(item_id)


create_want = JsonStorage.create_wishlist_item
create_bin = JsonStorage.create_bin_item
create_bin_item = JsonStorage.create_bin_item
create_wishlist_item = JsonStorage.create_wishlist_item
