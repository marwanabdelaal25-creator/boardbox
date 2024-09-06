"""Tests for boardbox.ratings."""

import pytest

from boardbox.errors import ValidationError
from boardbox.ratings import RatingsManager


def test_set_get_clear(populated_storage, sample_game):
    mgr = RatingsManager(populated_storage)
    mgr.set_rating(sample_game.id, 5, review="classic")
    row = mgr.get_rating(sample_game.id)
    assert row and row["stars"] == 5
    mgr.clear_rating(sample_game.id)
    assert mgr.get_rating(sample_game.id) is None


def test_top_average_distribution(populated_storage, sample_game, sample_game2):
    mgr = RatingsManager(populated_storage)
    mgr.set_rating(sample_game.id, 5)
    mgr.set_rating(sample_game2.id, 3)
    assert len(mgr.top_rated(min_stars=3)) >= 2
    assert mgr.average_rating() > 0
    dist = mgr.distribution()
    assert dist[5] >= 1 and dist[3] >= 1


def test_render_and_bulk(populated_storage, sample_game, sample_game2):
    mgr = RatingsManager(populated_storage)
    mgr.set_rating(sample_game.id, 4)
    assert "★" in mgr.render_top(limit=5)
    assert mgr.bulk_rate([sample_game2.id, "missing-id"], 2) >= 1


def test_set_invalid_rating(populated_storage, sample_game):
    mgr = RatingsManager(populated_storage)
    with pytest.raises(ValidationError):
        mgr.set_rating(sample_game.id, 0)
