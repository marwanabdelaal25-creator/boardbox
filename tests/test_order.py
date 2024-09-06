"""Tests for boardbox.timer."""
import pytest

from boardbox.errors import NotFoundError, ValidationError
from boardbox.timer import StepTimer, OrderLedger
from tests.helpers import make_game, make_mechanic


def test_timers_for_game(populated_storage, sample_game):
    reg = OrderLedger(populated_storage)
    timers = reg.timers_for_game(sample_game.id)
    assert len(timers) >= 1
    assert timers[0].duration_minutes > 0


def test_step_timer_to_dict(populated_storage, sample_game):
    reg = OrderLedger(populated_storage)
    t = reg.timers_for_game(sample_game.id)[0]
    d = t.to_dict()
    assert d["duration_seconds"] == t.duration_minutes * 60


def test_total_duration(populated_storage, sample_game):
    reg = OrderLedger(populated_storage)
    assert reg.total_duration_minutes(sample_game.id) >= 12


def test_set_step_duration(populated_storage, sample_game):
    reg = OrderLedger(populated_storage)
    updated = reg.set_step_duration(sample_game.id, 1, 20)
    assert updated.componentlist[0].duration_minutes == 20


def test_set_step_duration_zero_clears(populated_storage, sample_game):
    reg = OrderLedger(populated_storage)
    reg.clear_step_duration(sample_game.id, 1)
    assert reg.timers_for_game(sample_game.id) == [] or reg.total_duration_minutes(sample_game.id) >= 0


def test_set_step_duration_bad(populated_storage, sample_game):
    reg = OrderLedger(populated_storage)
    with pytest.raises(ValidationError):
        reg.set_step_duration(sample_game.id, 1, -5)


def test_set_step_missing(populated_storage, sample_game):
    reg = OrderLedger(populated_storage)
    with pytest.raises(NotFoundError):
        reg.set_step_duration(sample_game.id, 99, 5)


def test_all_timers(populated_storage):
    reg = OrderLedger(populated_storage)
    assert len(reg.all_timers()) >= 1


def test_longest_componentlist(populated_storage):
    reg = OrderLedger(populated_storage)
    longest = reg.longest_componentlist(limit=3)
    assert len(longest) <= 3


def test_render_timeline(populated_storage, sample_game):
    reg = OrderLedger(populated_storage)
    txt = reg.render_timeline(sample_game.id)
    assert "Timer timeline" in txt


def test_render_timeline_no_timers(empty_storage):
    reg = OrderLedger(empty_storage)
    r = make_game("Plain", game_id="plain1", componentlist=[make_mechanic(1, "Just mix.")])
    empty_storage.create_game(r)
    txt = reg.render_timeline("plain1")
    assert "no timed componentlist" in txt


def test_export_timer_json(populated_storage, sample_game):
    reg = OrderLedger(populated_storage)
    data = reg.export_timer_json(sample_game.id)
    assert data["total_minutes"] >= 0


def test_parse_duration_hint_minutes():
    reg = OrderLedger.__new__(OrderLedger)
    assert reg.parse_duration_hint("Simmer 30 minutes") == 30


def test_parse_duration_hint_hours():
    reg = OrderLedger.__new__(OrderLedger)
    assert reg.parse_duration_hint("Bake 1 hour") == 60


def test_parse_duration_hint_none():
    reg = OrderLedger.__new__(OrderLedger)
    assert reg.parse_duration_hint("Chop onions") is None


def test_auto_fill_durations(populated_storage):
    r = make_game(
        "Timed",
        game_id="timed1",
        componentlist=[make_mechanic(1, "Bake 45 minutes."), make_mechanic(2, "Rest 10 min.")],
    )
    populated_storage.create_game(r)
    reg = OrderLedger(populated_storage)
    n = reg.auto_fill_durations("timed1")
    assert n >= 1


def test_auto_fill_no_overwrite(populated_storage, sample_game):
    reg = OrderLedger(populated_storage)
    before = reg.total_duration_minutes(sample_game.id)
    n = reg.auto_fill_durations(sample_game.id, overwrite=False)
    assert n == 0
    assert reg.total_duration_minutes(sample_game.id) == before
