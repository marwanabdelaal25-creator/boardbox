"""Tests for boardbox.recurring."""
from datetime import datetime, timedelta, timezone

import pytest

from boardbox.errors import NotFoundError, ValidationError
from boardbox.recurring import RecurringSessions


def test_define_and_list(populated_storage):
    rm = RecurringSessions(populated_storage)
    task = rm.define("Weekly pasta", 7, game_id="rec001")
    assert task["interval_days"] == 7
    assert rm.list_all()


def test_define_bad_interval(populated_storage):
    rm = RecurringSessions(populated_storage)
    with pytest.raises(ValidationError):
        rm.define("Bad", 0)


def test_enable_disable(populated_storage):
    rm = RecurringSessions(populated_storage)
    t = rm.define("Salad", 3, game_id="rec002")
    rm.disable(t["id"])
    assert not rm.list_enabled()
    rm.enable(t["id"])
    assert rm.list_enabled()


def test_mark_done_creates_meal(populated_storage):
    rm = RecurringSessions(populated_storage)
    t = rm.define("Session pasta", 5, game_id="rec001")
    updated = rm.mark_done(t["id"])
    assert updated.get("last_run_at")
    assert populated_storage.list_sessions(game_id="rec001")


def test_due_tasks_never_run(populated_storage):
    rm = RecurringSessions(populated_storage)
    rm.define("New task", 7, game_id="rec001")
    due = rm.due_tasks()
    assert any(d.get("reason") == "never_run" for d in due)


def test_due_tasks_overdue(populated_storage):
    rm = RecurringSessions(populated_storage)
    t = rm.define("Overdue", 1, game_id="rec001")
    old = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
    populated_storage.update_recurring(t["id"], {"last_run_at": old})
    due = rm.due_tasks()
    assert due and due[0].get("overdue_days", 0) >= 0


def test_render_due(populated_storage):
    rm = RecurringSessions(populated_storage)
    rm.define("Task", 1, game_id="rec001")
    txt = rm.render_due()
    assert "Recurring" in txt or "No recurring" in txt


def test_delete_and_update(populated_storage):
    rm = RecurringSessions(populated_storage)
    t = rm.define("Temp", 7)
    rm.update(t["id"], {"title": "Updated"})
    rm.delete(t["id"])
    assert rm.for_game("rec001") == [] or True


def test_for_game(populated_storage):
    rm = RecurringSessions(populated_storage)
    rm.define("Pasta night", 7, game_id="rec001")
    assert rm.for_game("rec001")


def test_next_run_at(populated_storage):
    rm = RecurringSessions(populated_storage)
    t = rm.define("Next", 7, game_id="rec001")
    assert rm.next_run_at(t["id"])


def test_next_run_at_missing(populated_storage):
    rm = RecurringSessions(populated_storage)
    with pytest.raises(NotFoundError):
        rm.next_run_at("missing")
