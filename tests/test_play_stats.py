"""Tests for boardbox.play_stats."""

from datetime import datetime, timezone

from boardbox.play_log import ListeningSession
from boardbox.play_stats import (
    PlayStats,
    designer_session_totals,
    compare_months,
    dormant_games,
    format_session_report,
    genre_session_counts,
    load_play_stats,
    most_spun_games,
    parse_iso,
    sessions_by_month,
    sessions_per_hour,
    sessions_per_weekday,
    summary_text,
)
from tests.helpers import make_game


def test_play_stats_core(populated_storage, sample_game):
    ts = datetime.now(timezone.utc).isoformat()
    populated_storage.create_session({"id": "sp1", "game_id": sample_game.id, "played_at": ts})
    stats = load_play_stats(populated_storage)
    assert isinstance(stats.never_spun(), list)
    assert stats.most_spun(3)


def test_module_rollups(populated_storage, sample_game):
    ts = datetime.now(timezone.utc).isoformat()
    populated_storage.create_session({"id": "sp2", "game_id": sample_game.id, "played_at": ts})
    assert sessions_by_month(populated_storage)
    assert most_spun_games(populated_storage)
    assert sessions_per_weekday(populated_storage)
    assert designer_session_totals(populated_storage)
    assert summary_text(populated_storage)
    assert sessions_per_hour(populated_storage)
    assert genre_session_counts(populated_storage)
    assert format_session_report(populated_storage)
    assert compare_months(populated_storage, ts[:7], ts[:7])["delta"] == 0
    assert isinstance(dormant_games(populated_storage), list)


def test_direct_play_stats():
    game = make_game()
    session = ListeningSession(game_id=game.id)
    stats = PlayStats([game], [session])
    assert stats.most_spun(1)
    assert parse_iso(None) is None
    assert parse_iso("bad-date") is None
