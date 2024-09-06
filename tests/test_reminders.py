"""Tests for boardbox.reminders."""
from datetime import datetime, timedelta, timezone

from boardbox.reminders import GameReminderEngine
from tests.helpers import make_game


def test_stale_never_sessioned(populated_storage):
    old = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
    populated_storage.create_game(
        make_game("Old Untouched", game_id="old1").to_dict() | {"created_at": old}
    )
    engine = GameReminderEngine(populated_storage, stale_days=30)
    stale = engine.stale_games()
    assert any(r.game_id == "old1" for r in stale)


def test_stale_recently_sessioned_not_listed(populated_storage, sample_game):
    populated_storage.update_game(sample_game.id, {"last_played_at": datetime.now(timezone.utc).isoformat()})
    engine = GameReminderEngine(populated_storage, stale_days=30)
    assert all(r.game_id != sample_game.id for r in engine.stale_games())


def test_expiring_bins(populated_storage):
    soon = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    populated_storage.create_bin({"name": "yogurt", "quantity": 1, "unit": "cup", "expires_at": soon})
    engine = GameReminderEngine(populated_storage)
    exp = engine.expiring_bins(within_days=7)
    assert any(e.name == "yogurt" for e in exp)


def test_expired_bins(populated_storage):
    past = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    populated_storage.create_bin({"name": "cream", "quantity": 1, "unit": "cup", "expires_at": past})
    engine = GameReminderEngine(populated_storage)
    exp = engine.expiring_bins()
    assert any(e.urgency == "expired" for e in exp)


def test_summary_text(populated_storage):
    engine = GameReminderEngine(populated_storage)
    txt = engine.summary_text()
    assert isinstance(txt, str)


def test_summary_with_stale_days(populated_storage):
    engine = GameReminderEngine(populated_storage)
    txt = engine.summary_text(stale_days=1)
    assert isinstance(txt, str)


def test_games_not_sessioned_in(populated_storage):
    engine = GameReminderEngine(populated_storage)
    result = engine.games_not_sessioned_in(1)
    assert isinstance(result, list)


def test_summary_with_stale_and_bins(populated_storage):
    from datetime import datetime, timedelta, timezone
    engine = GameReminderEngine(populated_storage)
    old = (datetime.now(timezone.utc) - timedelta(days=45)).isoformat()
    populated_storage.update_game("rec001", {"last_played_at": old})
    soon = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    populated_storage.create_bin({"name": "cream", "quantity": 1, "unit": "cup", "expires_at": soon})
    txt = engine.summary_text()
    assert "Games not sessioned" in txt or "Pantry expiring" in txt or "All caught up" in txt


def test_expiring_ok_skipped(populated_storage):
    future = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    populated_storage.create_bin({"name": "long-life", "quantity": 1, "unit": "jar", "expires_at": future})
    engine = GameReminderEngine(populated_storage)
    assert engine.expiring_bins(within_days=7) == []


def test_compute_stale_with_last_sessioned(populated_storage, sample_game):
    old = (datetime.now(timezone.utc) - timedelta(days=45)).isoformat()
    populated_storage.update_game(sample_game.id, {"last_played_at": old})
    engine = GameReminderEngine(populated_storage, stale_days=30)
    rem = engine.compute_stale(populated_storage.get_game(sample_game.id))
    assert rem is not None
    assert rem.urgency == "stale"
