"""Tests for boardbox.backup."""

import json

import pytest

from boardbox.backup import CampaignBackup
from boardbox.errors import ExportError, StorageError


def test_create_and_list(populated_storage, tmp_path):
    bk = CampaignBackup(populated_storage.path, tmp_path / "backups")
    path = bk.create(studio="test")
    assert path.exists()
    assert len(bk.list_backups()) >= 1
    meta = path.with_suffix(".meta.json")
    assert meta.exists()


def test_export_import_snapshot(populated_storage, tmp_path):
    bk = CampaignBackup(populated_storage.path, tmp_path / "bk")
    snap = tmp_path / "snap.json"
    bk.export_snapshot(populated_storage, snap)
    populated_storage.create_game(
        {"id": "extra", "title": "Extra", "componentlist": [{"order": 1, "text": "x"}], "mechanics": []}
    )
    bk.import_snapshot(populated_storage, snap)
    from boardbox.errors import NotFoundError
    with pytest.raises(NotFoundError):
        populated_storage.get_game("extra")


def test_import_snapshot_bad_json(populated_storage, tmp_path):
    bk = CampaignBackup(populated_storage.path, tmp_path / "bk")
    bad = tmp_path / "bad.json"
    bad.write_text("not json", encoding="utf-8")
    with pytest.raises(ExportError):
        bk.import_snapshot(populated_storage, bad)


def test_prune_and_diff(populated_storage, tmp_path):
    bk = CampaignBackup(populated_storage.path, tmp_path / "bk")
    for i in range(3):
        bk.create(studio="b%d" % i)
    removed = bk.prune(keep=1)
    assert len(removed) >= 1
    latest = bk.list_backups()[0]
    diff = bk.diff_game_count(latest)
    assert "current_games" in diff


def test_diff_missing_file(tmp_path):
    bk = CampaignBackup(tmp_path / "nope.json", tmp_path / "bk")
    assert bk.diff_game_count(tmp_path / "missing.json")["error"] == "missing file"


def test_restore_and_latest(populated_storage, tmp_path):
    bk = CampaignBackup(populated_storage.path, tmp_path / "bk")
    backup = bk.create(studio="before")
    populated_storage.create_game(
        {"id": "temp99", "title": "Temp", "componentlist": [{"order": 1, "text": "x"}], "mechanics": []}
    )
    populated_storage.save()
    bk.restore(backup)
    populated_storage.load()
    games = populated_storage.list_games(active_only=False)
    assert all(r.id != "temp99" for r in games)


def test_restore_latest(populated_storage, tmp_path):
    bk = CampaignBackup(populated_storage.path, tmp_path / "bk")
    bk.create()
    safety = bk.restore_latest()
    assert safety.exists()


def test_restore_latest_empty(tmp_path):
    bk = CampaignBackup(tmp_path / "session.json", tmp_path / "bk")
    tmp_path.joinpath("session.json").write_text('{"schema_version": 2, "games": []}', encoding="utf-8")
    with pytest.raises(StorageError):
        bk.restore_latest()


def test_restore_corrupt_backup(populated_storage, tmp_path):
    bk = CampaignBackup(populated_storage.path, tmp_path / "bk")
    corrupt = tmp_path / "corrupt.json"
    corrupt.write_text("{bad", encoding="utf-8")
    with pytest.raises(StorageError):
        bk.restore(corrupt)


def test_restore_missing_raises(tmp_path):
    bk = CampaignBackup(tmp_path / "nope.json", tmp_path / "bk")
    with pytest.raises(StorageError):
        bk.create()


def test_rotate_weekly(populated_storage, tmp_path):
    bk = CampaignBackup(populated_storage.path, tmp_path / "bk")
    bk.create(studio="w1")
    bk.create(studio="w2")
    removed = bk.rotate_weekly(keep_weeks=1)
    assert isinstance(removed, list)


def test_peek_schema_version(populated_storage, tmp_path):
    bk = CampaignBackup(populated_storage.path, tmp_path / "bk")
    bp = bk.create()
    assert bk._peek_schema_version(bp) is not None
    assert bk._peek_schema_version(tmp_path / "missing.json") is None


def test_create_os_error(tmp_path, monkeypatch):
    import boardbox.backup as backup_mod
    path = tmp_path / "session.json"
    path.write_text('{"schema_version": 2, "games": []}', encoding="utf-8")
    bk = CampaignBackup(path, tmp_path / "bk")

    def boom(*args, **kwargs):
        raise OSError("copy failed")

    monkeypatch.setattr(backup_mod.shutil, "copy2", boom)
    with pytest.raises(StorageError):
        bk.create()


def test_restore_os_error(populated_storage, tmp_path, monkeypatch):
    import boardbox.backup as backup_mod
    bk = CampaignBackup(populated_storage.path, tmp_path / "bk")
    backup = bk.create()

    def boom(*args, **kwargs):
        raise OSError("restore failed")

    monkeypatch.setattr(backup_mod.shutil, "copy2", boom)
    with pytest.raises(StorageError):
        bk.restore(backup)


def test_diff_game_count(populated_storage, tmp_path):
    bk = CampaignBackup(populated_storage.path, tmp_path / "bk")
    backup = bk.create()
    diff = bk.diff_game_count(backup)
    assert diff["backup_games"] >= 0


def test_diff_game_count_missing(populated_storage, tmp_path):
    bk = CampaignBackup(populated_storage.path, tmp_path / "bk")
    assert bk.diff_game_count(tmp_path / "missing.json")["error"] == "missing file"


def test_import_snapshot_bad_json(populated_storage, tmp_path):
    from boardbox.errors import ExportError

    bk = CampaignBackup(populated_storage.path, tmp_path / "bk")
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(ExportError):
        bk.import_snapshot(populated_storage, bad)


def test_restore_corrupt_not_object(tmp_path):
    bk = CampaignBackup(tmp_path / "session.json", tmp_path / "bk")
    bk.library_path.write_text('{"schema_version": 2, "games": []}', encoding="utf-8")
    corrupt = tmp_path / "corrupt.json"
    corrupt.write_text("[1,2,3]", encoding="utf-8")
    with pytest.raises(StorageError):
        bk.restore(corrupt)
