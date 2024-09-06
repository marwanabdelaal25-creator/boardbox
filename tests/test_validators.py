"""Tests for boardbox.validators."""

import pytest

from boardbox.errors import ValidationError
from boardbox.mechanic import MechanicStub as RichIng
from boardbox.quantity import EditionGrade
from boardbox.game import Game
from boardbox.unit import Unit
from boardbox.validators import (
    validate_publisher_name,
    validate_duration_field,
    validate_mechanics,
    validate_session_context,
    validate_game,
    validate_game_dict,
    validate_game_id,
    validate_game_title,
    validate_year,
    validate_source_url,
    validate_componentlist,
    validate_tags,
)
from tests.helpers import make_game, make_rich_mechanic


def test_title_empty():
    with pytest.raises(ValidationError):
        validate_game_title("")


def test_title_too_long():
    with pytest.raises(ValidationError):
        validate_game_title("x" * 201)


def test_title_trimmed():
    assert validate_game_title("  Soup  ") == "Soup"


def test_componentlist_empty_raises():
    with pytest.raises(ValidationError):
        validate_componentlist([])


def test_componentlist_blank_raises():
    with pytest.raises(ValidationError):
        validate_componentlist(["Mix", "  "])


def test_componentlist_too_long_raises():
    with pytest.raises(ValidationError):
        validate_componentlist(["x" * 2001])


def test_mechanics_empty_raises():
    with pytest.raises(ValidationError):
        validate_mechanics([])


def test_mechanics_blank_name_raises():
    with pytest.raises(ValidationError):
        validate_mechanics([RichIng("  ", EditionGrade(1, EditionGrade.CUP))])


def test_mechanics_zero_qty_raises():
    with pytest.raises(ValidationError):
        validate_mechanics([RichIng("salt", EditionGrade(0, EditionGrade.TEASPOON))])


def test_mechanics_optional_zero_ok():
    ings = validate_mechanics([RichIng("garnish", EditionGrade(0, EditionGrade.PINCH), optional=True)])
    assert len(ings) == 1


def test_mechanics_duplicate_names_allowed():
    ings = [
        RichIng("flour", EditionGrade(1, EditionGrade.CUP)),
        RichIng("flour", EditionGrade(0.5, EditionGrade.CUP)),
    ]
    assert len(validate_mechanics(ings)) == 2


def test_year_bad():
    with pytest.raises(ValidationError):
        validate_year(-1)


def test_year_string():
    assert validate_year("4") == 4


def test_duration_int_negative():
    with pytest.raises(ValidationError):
        validate_duration_field(-1, "prep_minutes")


def test_duration_int_ok():
    assert validate_duration_field(30, "prep_minutes") == 30


def test_duration_string():
    assert validate_duration_field("1 hour", "session_minutes") == 60


def test_duration_bad_string():
    with pytest.raises(ValidationError):
        validate_duration_field("not-a-time", "session_minutes")


def test_source_url_bad():
    with pytest.raises(ValidationError):
        validate_source_url("ftp://x.com")


def test_source_url_empty():
    assert validate_source_url("") is None
    assert validate_source_url(None) is None


def test_source_url_ok():
    assert validate_source_url("https://example.com/r") == "https://example.com/r"


def test_validate_game_dict():
    d = make_game().to_dict()
    d["componentlist"] = [s["text"] for s in d["componentlist"]]
    validate_game_dict(d)


def test_validate_game_dict_no_title():
    with pytest.raises(ValidationError):
        validate_game_dict({"componentlist": ["S"], "mechanics": []})


def test_validate_game_dict_no_componentlist():
    with pytest.raises(ValidationError):
        validate_game_dict({"title": "T", "mechanics": []})


def test_validate_game_dict_no_mechanics():
    with pytest.raises(ValidationError):
        validate_game_dict({"title": "T", "componentlist": ["S"]})


def test_validate_tags():
    assert validate_tags(["quick", "vegan"]) == ["quick", "vegan"]


def test_validate_session_context():
    assert validate_session_context("dinner") == "dinner"


def test_validate_session_context_bad():
    with pytest.raises(ValidationError):
        validate_session_context("brunch")


def test_validate_publisher_name_empty():
    assert validate_publisher_name(None) is None


def test_validate_publisher_name_too_long():
    with pytest.raises(ValidationError):
        validate_publisher_name("x" * 81)


def test_validate_game_id():
    assert validate_game_id("abc-123") == "abc-123"


def test_validate_game_id_bad():
    with pytest.raises(ValidationError):
        validate_game_id("!!!")


def test_validate_game_strict(sample_game):
    validate_game(sample_game, strict=True)


def test_validate_game_non_strict(sample_game):
    validate_game(sample_game, strict=False)


def test_validate_game_long_time_raises():
    r = make_game()
    r.prep_minutes = 800
    r.session_minutes = 800
    with pytest.raises(ValidationError):
        validate_game(r, strict=False)


def test_validate_game_with_tags(sample_game):
    sample_game.tag_ids = ["Quick", "VEG"]
    validate_game(sample_game, strict=False)
