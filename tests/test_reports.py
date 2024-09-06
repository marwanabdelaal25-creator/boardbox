"""Tests for boardbox.reports."""

from datetime import datetime, timedelta, timezone

from boardbox.reports import WeeklySessionReport


def test_generate_empty(empty_storage):
    report = WeeklySessionReport(empty_storage).generate()
    assert report["totals"]["sessions_logged"] == 0


def test_generate_with_sessions(populated_storage, sample_game):
    now = datetime.now(timezone.utc).isoformat()
    populated_storage.create_session(
        {"id": "meal_r1", "game_id": sample_game.id, "played_at": now}
    )
    report = WeeklySessionReport(populated_storage).generate()
    assert report["totals"]["sessions_logged"] >= 1
    assert report["top_games"]


def test_render_text_and_markdown(populated_storage, sample_game):
    populated_storage.create_session(
        {
            "id": "meal_r2",
            "game_id": sample_game.id,
            "played_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    rpt = WeeklySessionReport(populated_storage)
    assert "Weekly" in rpt.render_text()
    assert "# Weekly" in rpt.render_markdown()


def test_compare_previous_week(populated_storage):
    ref = datetime.now(timezone.utc)
    cmp = WeeklySessionReport(populated_storage).compare_previous_week(ref)
    assert cmp["trend"] in ("up", "down", "flat")


def test_in_range_no_tz(populated_storage):
    rpt = WeeklySessionReport(populated_storage)
    start, end = rpt._week_bounds()
    assert not rpt._in_range(None, start, end)
    assert not rpt._in_range("bad-date", start, end)


def test_generate_old_meal_outdisc_num_week(populated_storage, sample_game):
    old = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()
    populated_storage.create_session({"id": "oldm", "game_id": sample_game.id, "played_at": old})
    report = WeeklySessionReport(populated_storage).generate()
    assert report["totals"]["sessions_logged"] == 0
