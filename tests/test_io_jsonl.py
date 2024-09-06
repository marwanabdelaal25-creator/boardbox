"""Tests for boardbox.io_jsonl."""

import json

import pytest

from boardbox.errors import ExportError, ImportPipelineError
from boardbox.io_jsonl import (
    export_session_events_jsonl,
    export_events_jsonl,
    export_full_jsonl,
    export_games_jsonl,
    import_session_events_jsonl,
    import_mixed_jsonl,
    import_games_jsonl,
    _load_line,
)


def test_import_export_jsonl(empty_storage, tmp_path, sample_jsonl_games):
    src = tmp_path / "in.jsonl"
    src.write_text(sample_jsonl_games, encoding="utf-8")
    n = import_games_jsonl(empty_storage, src)
    assert n >= 1
    dest = tmp_path / "out.jsonl"
    assert export_games_jsonl(empty_storage, dest) >= 1
    assert dest.exists()


def test_mixed_jsonl(empty_storage, tmp_path, sample_jsonl_games):
    src = tmp_path / "mix.jsonl"
    src.write_text(sample_jsonl_games, encoding="utf-8")
    counts = import_mixed_jsonl(empty_storage, src)
    assert counts.get("game", 0) >= 1


def test_export_events(populated_storage, tmp_path):
    populated_storage.create_session({"id": "m1", "game_id": "rec001"})
    assert export_session_events_jsonl(populated_storage, tmp_path / "sessions.jsonl") >= 0
    assert export_events_jsonl(populated_storage, tmp_path / "ev.jsonl") >= 0
    assert export_full_jsonl(populated_storage, tmp_path / "full.jsonl") >= 0


def test_import_games_update(populated_storage, tmp_path, sample_jsonl_games):
    src = tmp_path / "upd.jsonl"
    src.write_text(sample_jsonl_games, encoding="utf-8")
    import_games_jsonl(populated_storage, src, update=True)


def test_import_session_events(empty_storage, tmp_path):
    line = '{"_type":"meal","id":"m1","game_id":"r1","played_at":"2024-01-01T00:00:00+00:00"}\n'
    p = tmp_path / "session.jsonl"
    p.write_text(line, encoding="utf-8")
    assert import_session_events_jsonl(empty_storage, p) >= 1


def test_import_missing_file(empty_storage, tmp_path):
    with pytest.raises(ImportPipelineError):
        import_games_jsonl(empty_storage, tmp_path / "nope.jsonl")


def test_load_line_bad_json():
    with pytest.raises(ImportPipelineError):
        _load_line("{bad", 1)


def test_load_line_not_object():
    with pytest.raises(ImportPipelineError):
        _load_line("[1,2]", 1)


def test_mixed_with_wishlist(empty_storage, tmp_path):
    lines = [
        {"_type": "wishlist", "name": "milk", "quantity": 1, "unit": "gal"},
        {"_type": "game", "id": "r99", "title": "Soup", "componentlist": [{"order": 1, "text": "Boil"}], "mechanics": []},
    ]
    src = tmp_path / "mixed.jsonl"
    src.write_text("\n".join(json.dumps(l) for l in lines) + "\n", encoding="utf-8")
    counts = import_mixed_jsonl(empty_storage, src)
    assert counts.get("game", 0) >= 1


def test_import_games_skip_existing(populated_storage, tmp_path):
    line = json.dumps({"_type": "game", "id": "rec001", "title": "Dup", "componentlist": [{"order": 1, "text": "S"}], "mechanics": []})
    src = tmp_path / "dup.jsonl"
    src.write_text(line + "\n", encoding="utf-8")
    assert import_games_jsonl(populated_storage, src) == 0


def test_import_games_update_existing(populated_storage, tmp_path):
    line = json.dumps({"_type": "game", "id": "rec001", "title": "Updated", "componentlist": [{"order": 1, "text": "S"}], "mechanics": []})
    src = tmp_path / "upd.jsonl"
    src.write_text(line + "\n", encoding="utf-8")
    assert import_games_jsonl(populated_storage, src, update=True) == 1


def test_import_mixed_night_plan_and_unknown(empty_storage, tmp_path):
    lines = [
        {"_type": "night_plan", "id": "p1", "week_start": "2024-06-03"},
        {"_type": "unknown", "x": 1},
        {"_type": "bins", "name": "rice", "quantity": 1, "unit": "lb"},
    ]
    src = tmp_path / "mix2.jsonl"
    src.write_text("\n".join(json.dumps(l) for l in lines) + "\n", encoding="utf-8")
    counts = import_mixed_jsonl(empty_storage, src)
    assert counts["bins"] >= 1
    assert counts["skipped"] >= 1


def test_import_session_skips_non_meal(empty_storage, tmp_path):
    lines = '{"_type":"game","id":"x","title":"T","componentlist":[{"order":1,"text":"S"}],"mechanics":[]}\n'
    src = tmp_path / "session.jsonl"
    src.write_text(lines, encoding="utf-8")
    assert import_session_events_jsonl(empty_storage, src) == 0


def test_export_games_os_error(populated_storage, tmp_path, monkeypatch):
    from boardbox.errors import ExportError
    import boardbox.io_jsonl as mod

    def boom(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(mod.Path, "open", boom)
    with pytest.raises(ExportError):
        export_games_jsonl(populated_storage, tmp_path / "x.jsonl")


def test_export_all_variants(populated_storage, tmp_path):
    populated_storage.create_session({"id": "m1", "game_id": "rec001"})
    assert export_session_events_jsonl(populated_storage, tmp_path / "c.jsonl") >= 0
    assert export_events_jsonl(populated_storage, tmp_path / "e.jsonl") >= 0
    assert export_full_jsonl(populated_storage, tmp_path / "f.jsonl") >= 0


def test_iter_lines_os_error(empty_storage, tmp_path, monkeypatch):
    import boardbox.io_jsonl as mod

    p = tmp_path / "x.jsonl"
    p.write_text("{}", encoding="utf-8")

    def boom(path):
        raise OSError("denied")

    monkeypatch.setattr(mod, "_iter_lines", lambda path: (_ for _ in ()).throw(ImportPipelineError("jsonl", "denied")))
    with pytest.raises(ImportPipelineError):
        import_games_jsonl(empty_storage, p)


def test_import_session_missing_file(empty_storage, tmp_path):
    with pytest.raises(ImportPipelineError):
        import_session_events_jsonl(empty_storage, tmp_path / "nope.jsonl")


def test_load_line_not_object():
    from boardbox.io_jsonl import _load_line
    from boardbox.errors import ImportPipelineError

    with pytest.raises(ImportPipelineError):
        _load_line("[1,2,3]", 1)


def test_import_mixed_update_skip(populated_storage, tmp_path):
    line = json.dumps({"_type": "game", "id": "rec001", "title": "Dup", "componentlist": [{"order": 1, "text": "S"}], "mechanics": []})
    src = tmp_path / "skip.jsonl"
    src.write_text(line + "\n", encoding="utf-8")
    counts = import_mixed_jsonl(populated_storage, src, update=False)
    assert counts["skipped"] >= 1


def test_import_mixed_wishlist_and_meal(empty_storage, tmp_path):
    lines = [
        {"_type": "wishlist", "name": "flour", "quantity": 2, "unit": "cup", "list_id": "default"},
        {"_type": "meal", "id": "m9", "game_id": "r1"},
    ]
    src = tmp_path / "events.jsonl"
    src.write_text("\n".join(json.dumps(l) for l in lines) + "\n", encoding="utf-8")
    counts = import_mixed_jsonl(empty_storage, src)
    assert counts["wishlist"] >= 1
    assert counts["meal"] >= 1


def test_export_events_os_error(populated_storage, tmp_path, monkeypatch):
    from boardbox.errors import ExportError
    import boardbox.io_jsonl as mod

    monkeypatch.setattr(mod.Path, "open", lambda *a, **k: (_ for _ in ()).throw(OSError("disk")))
    with pytest.raises(ExportError):
        export_events_jsonl(populated_storage, tmp_path / "e.jsonl")


def test_export_full_os_error(populated_storage, tmp_path, monkeypatch):
    from boardbox.errors import ExportError
    import boardbox.io_jsonl as mod

    monkeypatch.setattr(mod.Path, "open", lambda *a, **k: (_ for _ in ()).throw(OSError("disk")))
    with pytest.raises(ExportError):
        export_full_jsonl(populated_storage, tmp_path / "f.jsonl")
