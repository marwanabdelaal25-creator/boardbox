"""Tests for boardbox.archive."""
import pytest

from boardbox.archive import ArchiveManager
from boardbox.errors import NotFoundError, ValidationError


def test_archive_restore_cycle(populated_storage):
    mgr = ArchiveManager(populated_storage)
    entry = mgr.archive_game("rec002", reason="test")
    assert entry.get("entity_id") == "rec002"
    data = mgr.restore_game("rec002")
    assert data.get("archived") is False


def test_archive_twice_raises(populated_storage):
    mgr = ArchiveManager(populated_storage)
    mgr.archive_game("rec001")
    with pytest.raises(ValidationError):
        mgr.archive_game("rec001")


def test_restore_not_archived(populated_storage):
    mgr = ArchiveManager(populated_storage)
    with pytest.raises(ValidationError):
        mgr.restore_game("rec001")


def test_list_and_stats(populated_storage):
    mgr = ArchiveManager(populated_storage)
    mgr.archive_game("rec001")
    assert mgr.list_archived_games()
    assert mgr.stats()["archived_games"] >= 1


def test_get_snapshot_and_restore(populated_storage):
    mgr = ArchiveManager(populated_storage)
    entry = mgr.archive_game("rec001")
    snap = mgr.get_snapshot(entry["id"])
    assert snap.get("title")
    restored = mgr.restore_from_snapshot(entry["id"], new_id=True)
    assert restored.get("archived") is False


def test_permanent_delete(populated_storage):
    mgr = ArchiveManager(populated_storage)
    with pytest.raises(ValidationError):
        mgr.permanently_delete_game("rec002")
    mgr.permanently_delete_game("rec002", confirm=True)
    with pytest.raises(NotFoundError):
        populated_storage.get_game("rec002")


def test_bulk_archive_and_purge(populated_storage):
    mgr = ArchiveManager(populated_storage)
    results = mgr.bulk_archive(["rec001", "missing"])
    assert results
    assert mgr.purge_old_entries(keep=0, dry_run=True) >= 0


def test_purge_apply(populated_storage):
    mgr = ArchiveManager(populated_storage)
    for i in range(3):
        mgr.archive_game("rec001", reason=f"r{i}")
        mgr.restore_game("rec001")
    removed = mgr.purge_old_entries(keep=1, dry_run=False)
    assert removed >= 0


def test_export_text(populated_storage):
    mgr = ArchiveManager(populated_storage)
    mgr.archive_game("rec001")
    txt = mgr.export_archived_text()
    assert "Sunday Pasta" in txt or "rec001" in txt
