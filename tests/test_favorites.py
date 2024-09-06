"""Tests for boardbox.favorites."""
import pytest

from boardbox.errors import NotFoundError
from boardbox.favorites import FavoritesManager


def test_add_remove_toggle(populated_storage):
    fm = FavoritesManager(populated_storage)
    fm.remove("rec002")
    fm.add("rec002")
    assert fm.is_favorite("rec002")
    assert fm.toggle("rec002") is False


def test_add_not_found(populated_storage):
    fm = FavoritesManager(populated_storage)
    with pytest.raises(NotFoundError):
        fm.add("missing")


def test_list_games(populated_storage):
    fm = FavoritesManager(populated_storage)
    recs = fm.list_games()
    assert any(r.id == "rec001" for r in recs)


def test_sync_flags(populated_storage):
    fm = FavoritesManager(populated_storage)
    n = fm.sync_flags()
    assert n >= 0


def test_prune_stale(populated_storage):
    fm = FavoritesManager(populated_storage)
    populated_storage.add_favorite("ghost-id")
    removed = fm.prune_stale()
    assert "ghost-id" in removed


def test_top_by_publisher_name(populated_storage):
    fm = FavoritesManager(populated_storage)
    recs = fm.top_by_publisher_name("italian")
    assert isinstance(recs, list)


def test_count_and_render(populated_storage):
    fm = FavoritesManager(populated_storage)
    assert fm.count() >= 1
    txt = fm.render_list()
    assert "Favorite" in txt or "★" in txt


def test_bulk_add(populated_storage):
    fm = FavoritesManager(populated_storage)
    fm.remove("rec002")
    n = fm.bulk_add(["rec002", "bad-id"])
    assert n >= 1


def test_remove_missing_game(populated_storage):
    fm = FavoritesManager(populated_storage)
    populated_storage.add_favorite("orphan")
    ids = fm.remove("orphan")
    assert "orphan" not in ids


def test_list_ids(populated_storage):
    fm = FavoritesManager(populated_storage)
    assert "rec001" in fm.list_ids()
