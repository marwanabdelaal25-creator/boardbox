"""Tests for boardbox.audit_log."""
from boardbox.audit_log import AuditLog


def test_record_and_list(populated_storage):
    log = AuditLog(populated_storage)
    entry = log.record("update", "games", "rec001", details={"k": 1})
    assert entry.get("action") == "update"
    assert log.list_entries(entity="games", limit=3)


def test_since_and_history(populated_storage):
    log = AuditLog(populated_storage)
    log.record("session", "games", "rec001")
    assert log.since("1970-01-01T00:00:00+00:00")
    assert log.game_history("rec001")


def test_wrap_mutation(populated_storage):
    log = AuditLog(populated_storage)
    out = log.wrap_mutation("patch", "games", "rec001", lambda: populated_storage.get_game("rec001").title)
    assert out


def test_export_and_counts(populated_storage):
    log = AuditLog(populated_storage)
    log.record("export", "sessionbook", "main")
    txt = log.export_text(limit=10)
    assert "export" in txt or "sessionbook" in txt
    assert log.count_by_action().get("export", 0) >= 1


def test_prune_dry_run(populated_storage):
    log = AuditLog(populated_storage)
    for i in range(5):
        log.record(f"act{i}", "games", "rec001")
    assert log.prune_old(keep=2, dry_run=True) >= 0


def test_prune_apply(populated_storage):
    log = AuditLog(populated_storage)
    for i in range(5):
        log.record(f"act{i}", "games", "rec001")
    removed = log.prune_old(keep=2, dry_run=False)
    assert removed >= 1
    assert len(populated_storage.list_audit()) <= 2


def test_export_empty(empty_storage):
    log = AuditLog(empty_storage)
    assert "(empty audit log)" in log.export_text()
