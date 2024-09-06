"""Tests for boardbox.io_bgg."""
import json

import pytest

from boardbox.errors import ImportPipelineError, ValidationError
from boardbox.io_bgg import (
    _iter_paprika_games,
    _game_from_paprika,
    _split_lines,
    import_bgg_csv,
)


def test_import_bgg_csv(empty_storage, tmp_path, sample_bgg_json):
    p = tmp_path / "p.json"
    p.write_text(sample_bgg_json, encoding="utf-8")
    assert import_bgg_csv(empty_storage, p) >= 1


def test_import_bgg_csv_update(populated_storage, tmp_path, sample_bgg_json):
    p = tmp_path / "p.json"
    p.write_text(sample_bgg_json, encoding="utf-8")
    import_bgg_csv(populated_storage, p)
    assert import_bgg_csv(populated_storage, p, update=True) >= 0


def test_import_missing_file(empty_storage, tmp_path):
    with pytest.raises(ImportPipelineError):
        import_bgg_csv(empty_storage, tmp_path / "nope.json")


def test_import_bad_json(empty_storage, tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("not json", encoding="utf-8")
    with pytest.raises(ImportPipelineError):
        import_bgg_csv(empty_storage, p)


def test_import_os_error(empty_storage, tmp_path, monkeypatch):
    p = tmp_path / "p.json"
    p.write_text("{}", encoding="utf-8")

    def boom(*args, **kwargs):
        raise OSError("read denied")

    monkeypatch.setattr(type(p), "read_text", boom)
    with pytest.raises(ImportPipelineError):
        import_bgg_csv(empty_storage, p)


def test_game_from_paprika_minimal():
    data = _game_from_paprika({
        "name": "Stew",
        "mechanics": ["2 cups broth"],
        "directions": ["Simmer"],
        "year": 4,
        "categories": ["comfort"],
        "source": "https://example.com",
    })
    assert data["title"] == "Stew"


def test_game_from_paprika_no_title():
    with pytest.raises(ValidationError):
        _game_from_paprika({"mechanics": ["salt"]})


def test_game_from_paprika_format_string():
    data = _game_from_paprika({
        "name": "Tagged",
        "mechanics": [],
        "directions": ["Session"],
        "categories": "Italian, Quick",
    })
    assert "italian" in data["tag_ids"]


def test_split_lines_variants():
    assert _split_lines(None) == []
    assert _split_lines(["a", "", "b"]) == ["a", "b"]
    assert _split_lines("one\ntwo") == ["one", "two"]


def test_iter_paprika_list_and_dict():
    games = list(_iter_paprika_games({"games": [{"name": "A", "mechanics": [], "directions": ["S"]}]}))
    assert len(games) == 1
    single = list(_iter_paprika_games({"name": "Solo", "mechanics": [], "directions": ["Session"]}))
    assert len(single) == 1


def test_iter_paprika_nested_uid_map():
    payload = {"uid42": {"name": "Nested", "mechanics": ["salt"], "directions": ["Mix"]}}
    games = list(_iter_paprika_games(payload))
    assert len(games) == 1
    assert games[0].get("uid") == "uid42"


def test_import_list_payload(empty_storage, tmp_path):
    payload = [{"name": "List Stew", "mechanics": ["1 cup broth"], "directions": ["Simmer"]}]
    p = tmp_path / "list.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    assert import_bgg_csv(empty_storage, p) >= 1


def test_import_skip_existing_uid(empty_storage, tmp_path):
    payload = [{"uid": "fixed01", "name": "Once", "mechanics": ["salt"], "directions": ["Session"]}]
    p = tmp_path / "fixed.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    assert import_bgg_csv(empty_storage, p) == 1
    assert import_bgg_csv(empty_storage, p, update=False) == 0
    assert len(empty_storage.list_games()) == 1


def test_import_validation_error(empty_storage, tmp_path):
    payload = [{"mechanics": ["salt"], "directions": ["Session"]}]
    p = tmp_path / "bad.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ImportPipelineError):
        import_bgg_csv(empty_storage, p)
