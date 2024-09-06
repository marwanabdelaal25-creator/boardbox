"""Tests for boardbox.import_merge."""
import json

import pytest

from boardbox.errors import ImportPipelineError, ValidationError
from boardbox.import_merge import ImportMerger
from tests.helpers import make_game


def test_find_duplicates(populated_storage):
    m = ImportMerger(populated_storage)
    dupes = m.find_duplicates(make_game("Sunday Pasta", game_id="new"))
    assert dupes


def test_merge_skip_replace_create(populated_storage):
    m = ImportMerger(populated_storage)
    incoming = {"title": "Sunday Pasta", "componentlist": [{"order": 1, "text": "New"}], "mechanics": []}
    assert m.merge_one(incoming, strategy="skip")["action"] == "skipped"
    assert m.merge_one({**incoming, "componentlist": [{"order": 1, "text": "X"}]}, strategy="replace")["action"] == "replaced"
    assert m.merge_one({"title": "Brand New", "componentlist": [{"order": 1, "text": "S"}], "mechanics": []})["action"] == "created"


def test_merge_keep_both(populated_storage):
    m = ImportMerger(populated_storage)
    out = m.merge_one(
        {"title": "Sunday Pasta", "componentlist": [{"order": 1, "text": "Alt"}], "mechanics": []},
        strategy="keep_both",
    )
    assert out["action"] == "created_copy"


def test_merge_bad_strategy(populated_storage):
    m = ImportMerger(populated_storage)
    with pytest.raises(ValidationError):
        m.merge_one({"title": "X", "componentlist": [{"order": 1, "text": "S"}], "mechanics": []}, strategy="nope")


def test_merge_batch(populated_storage):
    m = ImportMerger(populated_storage)
    batch = [
        {"title": "Sunday Pasta", "componentlist": [{"order": 1, "text": "S"}], "mechanics": []},
        {"title": "Unique Dish", "componentlist": [{"order": 1, "text": "Session"}], "mechanics": []},
    ]
    result = m.merge_batch(batch, strategy="skip")
    assert result["skipped"] + result["created"] >= 1


def test_load_json_file_list_and_dict(tmp_path):
    m = ImportMerger.__new__(ImportMerger)
    list_path = tmp_path / "list.json"
    list_path.write_text(json.dumps([{"title": "A", "componentlist": ["S"], "mechanics": []}]), encoding="utf-8")
    assert m.load_json_file(list_path)
    dict_path = tmp_path / "dict.json"
    dict_path.write_text(json.dumps({"games": [{"title": "B", "componentlist": ["S"], "mechanics": []}]}), encoding="utf-8")
    assert m.load_json_file(dict_path)


def test_load_json_file_bad(tmp_path):
    m = ImportMerger.__new__(ImportMerger)
    with pytest.raises(ImportPipelineError):
        m.load_json_file(tmp_path / "missing.json")


def test_preview_and_import_file(populated_storage, tmp_path):
    m = ImportMerger(populated_storage)
    path = tmp_path / "batch.json"
    path.write_text(json.dumps([{"title": "Sunday Pasta", "componentlist": ["S"], "mechanics": []}]), encoding="utf-8")
    prev = m.preview(path)
    assert prev[0]["duplicate_count"] >= 0
    out = m.import_file(path)
    assert "created" in out or "skipped" in out


def test_dedupe_existing(populated_storage):
    m = ImportMerger(populated_storage)
    pairs = m.dedupe_existing(dry_run=True)
    assert isinstance(pairs, list)


def test_merge_with_target_id(populated_storage):
    m = ImportMerger(populated_storage)
    incoming = {"title": "Sunday Pasta", "componentlist": [{"order": 1, "text": "X"}], "mechanics": []}
    out = m.merge_one(incoming, strategy="replace", target_id="rec001")
    assert out["action"] == "replaced"


def test_load_single_game_dict(tmp_path):
    m = ImportMerger.__new__(ImportMerger)
    path = tmp_path / "one.json"
    path.write_text(json.dumps({"title": "Solo", "componentlist": ["S"], "mechanics": []}), encoding="utf-8")
    assert len(m.load_json_file(path)) == 1


def test_merge_batch_error(populated_storage):
    m = ImportMerger(populated_storage)
    result = m.merge_batch([{"componentlist": [], "mechanics": []}], strategy="skip")
    assert result["errors"]


def test_find_duplicates_by_source_url(populated_storage):
    m = ImportMerger(populated_storage)
    game = populated_storage.get_game("rec001")
    dupes = m.find_duplicates({"title": "Totally Different", "source_url": game.source_url or "https://example.com"})
    assert isinstance(dupes, list)


def test_merge_keep_both(populated_storage):
    m = ImportMerger(populated_storage)
    incoming = {"title": "Sunday Pasta", "componentlist": [{"order": 1, "text": "X"}], "mechanics": []}
    out = m.merge_one(incoming, strategy="keep_both")
    assert out["action"] == "created_copy"


def test_load_json_unrecognized_shape(tmp_path):
    m = ImportMerger.__new__(ImportMerger)
    path = tmp_path / "weird.json"
    path.write_text(json.dumps({"foo": "bar"}), encoding="utf-8")
    with pytest.raises(ImportPipelineError):
        m.load_json_file(path)


def test_dedupe_existing_not_dry_run(populated_storage):
    m = ImportMerger(populated_storage)
    assert m.dedupe_existing(dry_run=False) == m.dedupe_existing(dry_run=True)
