"""Tests for boardbox.seasonal."""
from datetime import datetime

from boardbox.seasonal import SeasonalFilter, SEASONAL_PRODUCE


def test_current_season():
    sf = SeasonalFilter.__new__(SeasonalFilter)
    assert sf.current_season(datetime(2024, 7, 15)) == "summer"


def test_normalize_season():
    sf = SeasonalFilter.__new__(SeasonalFilter)
    assert sf.normalize_season("Fall") == "autumn"


def test_tag_and_filter(populated_storage):
    sf = SeasonalFilter(populated_storage)
    sf.tag_game("rec001", ["summer", "fall"])
    hits = sf.filter_by_season("summer")
    assert any(r.id == "rec001" for r in hits)


def test_add_remove_season(populated_storage):
    sf = SeasonalFilter(populated_storage)
    sf.add_season("rec002", "winter")
    sf.remove_season("rec002", "winter")
    assert "winter" not in populated_storage.get_game("rec002").seasonal_tags


def test_in_season_now(populated_storage):
    sf = SeasonalFilter(populated_storage)
    sf.tag_game("rec001", [sf.current_season()])
    assert sf.in_season_now()


def test_season_counts(populated_storage):
    sf = SeasonalFilter(populated_storage)
    sf.tag_game("rec001", ["spring"])
    counts = sf.season_counts()
    assert counts["spring"] >= 1


def test_suggest_for_produce():
    sf = SeasonalFilter.__new__(SeasonalFilter)
    seasons = sf.suggest_for_produce("tomato")
    assert "summer" in seasons


def test_auto_tag_from_mechanics(populated_storage):
    sf = SeasonalFilter(populated_storage)
    inferred = sf.auto_tag_from_mechanics("rec001", apply=True)
    assert isinstance(inferred, list)


def test_render_seasonal_menu(populated_storage):
    sf = SeasonalFilter(populated_storage)
    sf.tag_game("rec001", ["summer"])
    txt = sf.render_seasonal_menu("summer")
    assert "In-season" in txt


def test_render_empty_season(empty_storage):
    sf = SeasonalFilter(empty_storage)
    txt = sf.render_seasonal_menu("winter")
    assert "none tagged" in txt


def test_untagged_games(populated_storage):
    sf = SeasonalFilter(populated_storage)
    untagged = sf.untagged_games()
    assert isinstance(untagged, list)


def test_seasonal_produce_keys():
    assert "summer" in SEASONAL_PRODUCE
