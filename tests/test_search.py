"""Tests for boardbox.search."""
from boardbox.search import GameSearch, SearchHit


def test_search_games(populated_storage):
    s = GameSearch(populated_storage)
    hits = s.search_games("pasta")
    assert hits and hits[0].score > 0


def test_search_games_empty_query(populated_storage):
    assert GameSearch(populated_storage).search_games("") == []


def test_search_by_field(populated_storage):
    hits = GameSearch(populated_storage).search_games("Boil", field="componentlist")
    assert isinstance(hits, list)


def test_search_by_mechanic(populated_storage):
    hits = GameSearch(populated_storage).search_by_mechanic("tomato")
    assert isinstance(hits, list)


def test_search_notes(populated_storage):
    hits = GameSearch(populated_storage).search_notes("Family")
    assert isinstance(hits, list)


def test_search_all_and_limit(populated_storage):
    s = GameSearch(populated_storage)
    hits = s.search_all("pasta", limit=1)
    assert len(hits) <= 1


def test_suggest_titles(populated_storage):
    titles = GameSearch(populated_storage).suggest_titles("Sun")
    assert titles


def test_suggest_empty(empty_storage):
    assert GameSearch(empty_storage).suggest_titles("") == []


def test_to_dicts():
    hits = [SearchHit("game", "r1", "Soup", "snippet", 0.5, "title")]
    d = GameSearch.__new__(GameSearch).to_dicts(hits)
    assert d[0]["kind"] == "game"


def test_filter_publisher_name_format(populated_storage):
    s = GameSearch(populated_storage)
    assert s.filter_publisher_name("italian")
    assert s.filter_format("main")
