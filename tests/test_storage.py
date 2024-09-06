"""Tests for boardbox.storage."""
import json

import pytest

from boardbox.errors import NotFoundError, StorageError, ValidationError
from boardbox.storage import JsonStorage, DEFAULT_COOKBOOK, SCHEMA_VERSION
from tests.helpers import make_game, make_campaign_dict, make_bins_item


def test_default_schema_version():
    assert DEFAULT_COOKBOOK["schema_version"] == SCHEMA_VERSION


def test_empty_storage_creates_file(empty_storage, tmp_library_path):
    assert tmp_library_path.exists()


def test_create_and_get_game(empty_storage):
    r = make_game()
    empty_storage.create_game(r)
    got = empty_storage.get_game(r.id)
    assert got.title == r.title


def test_list_games_active_only(populated_storage, sample_game):
    populated_storage.update_game(sample_game.id, {"archived": True})
    active = populated_storage.list_games(active_only=True)
    assert all(not x.archived for x in active)


def test_duplicate_game_id(empty_storage):
    r = make_game()
    empty_storage.create_game(r)
    with pytest.raises(ValidationError):
        empty_storage.create_game(r.to_dict())


def test_snapshot_and_replace(empty_storage):
    snap = empty_storage.snapshot()
    snap["games"] = []
    empty_storage.replace_all(snap)
    assert empty_storage.list_games() == []


def test_mutate(empty_storage):
    def fn(data):
        data.setdefault("notes", []).append({"id": "n1", "body": "x"})

    empty_storage.mutate(fn)
    assert len(empty_storage.list_notes()) >= 1


def test_favorites(populated_storage, sample_game):
    favs = populated_storage.list_favorites()
    assert sample_game.id in favs
    populated_storage.remove_favorite(sample_game.id)
    assert sample_game.id not in populated_storage.list_favorites()


def test_meal_updates_last_sessioned(empty_storage):
    r = make_game()
    empty_storage.create_game(r)
    empty_storage.create_session({"id": "m1", "game_id": r.id})
    updated = empty_storage.get_game(r.id)
    assert updated.last_played_at


def test_corrupt_bucket_raises(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"schema_version": 2, "games": "nope"}), encoding="utf-8")
    storage = JsonStorage(path)
    with pytest.raises(StorageError):
        storage.list_games()


def test_invalid_json_raises(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{", encoding="utf-8")
    with pytest.raises(StorageError):
        JsonStorage(path)


def test_non_object_root_raises(tmp_path):
    path = tmp_path / "list.json"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(StorageError):
        JsonStorage(path)


def test_mechanic_crud(empty_storage):
    ing = empty_storage.create_mechanic({"id": "ing1", "name": "garlic"})
    assert empty_storage.get_mechanic("ing1")["name"] == "garlic"
    empty_storage.update_mechanic("ing1", {"name": "garlic clove"})
    empty_storage.delete_mechanic("ing1")
    with pytest.raises(NotFoundError):
        empty_storage.get_mechanic("ing1")


def test_night_plan_crud(empty_storage):
    plan = empty_storage.create_session_plan(make_campaign_dict())
    pid = plan["id"]
    assert empty_storage.get_session_plan(pid)["id"] == pid
    empty_storage.update_night_plan(pid, {"notes": "updated"})
    empty_storage.delete_session_plan(pid)


def test_wishlist_crud(empty_storage):
    item = empty_storage.create_want({"name": "milk", "quantity": 1, "list_id": "default"})
    iid = item["id"]
    rows = empty_storage.list_want(list_id="default")
    assert rows
    empty_storage.update_want(iid, {"checked": True})
    empty_storage.delete_want(iid)


def test_tags_notes_bins(empty_storage):
    empty_storage.create_tag({"id": "t1", "name": "quick"})
    empty_storage.update_tag("t1", {"name": "fast"})
    empty_storage.delete_tag("t1")
    empty_storage.create_note({"id": "n1", "body": "note", "game_id": "r1"})
    empty_storage.update_note("n1", {"body": "updated"})
    empty_storage.delete_note("n1")
    pan = empty_storage.create_bin(make_bins_item())
    empty_storage.update_bin(pan["id"], {"quantity": 2})
    empty_storage.delete_bin(pan["id"])


def test_audit_append(empty_storage):
    entry = empty_storage.append_audit({"action": "test"})
    assert entry.get("id", "").startswith("aud_")


def test_plugins_recurring_campaigns(empty_storage):
    p = empty_storage.upsert_plugin({"id": "pl1", "name": "Demo", "hooks": []})
    empty_storage.upsert_plugin({"id": "pl1", "enabled": False})
    empty_storage.delete_plugin("pl1")
    t = empty_storage.create_recurring({"title": "Weekly", "interval_days": 7})
    empty_storage.update_recurring(t["id"], {"title": "Biweekly"})
    empty_storage.delete_recurring(t["id"])
    c = empty_storage.create_campaign({"id": "c1", "name": "Weeknight", "game_ids": []})
    empty_storage.update_campaign("c1", {"name": "Faves"})
    empty_storage.delete_campaign("c1")


def test_normalize_game_tags_alias(empty_storage):
    r = empty_storage.create_game({"id": "r1", "title": "T", "tags": ["a"], "componentlist": [{"order": 1, "text": "s"}], "mechanics": []})
    got = empty_storage.get_game("r1")
    assert got.tag_ids == ["a"]


def test_list_sessions_filtered(empty_storage):
    r = make_game()
    empty_storage.create_game(r)
    empty_storage.create_session({"id": "m1", "game_id": r.id})
    assert empty_storage.list_sessions(game_id=r.id)
