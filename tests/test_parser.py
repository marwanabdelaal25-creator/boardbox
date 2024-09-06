"""Tests for boardbox.parser."""

from datetime import date

import pytest

from boardbox.errors import ParseError
from boardbox.parser import (
    format_duration,
    format_year,
    parse_duration,
    parse_format_pair,
    parse_mechanic_line,
    parse_duration,
    parse_date,
    parse_datetime,
    parse_quantity,
    parse_year,
    try_parse_date,
)


@pytest.mark.parametrize(
    "raw,minutes",
    [
        ("30m", 30),
        ("1h", 60),
        ("1h15m", 75),
        ("90", 90),
        ("1:30", 90),
        ("2 hours", 120),
    ],
)
def test_parse_duration(raw, minutes):
    assert parse_duration(raw) == minutes


@pytest.mark.parametrize("raw", ["", "0m", "nope", "-5m"])
def test_parse_duration_bad(raw):
    with pytest.raises(ParseError):
        parse_duration(raw)


def test_parse_format_pair_split():
    prep, session = parse_format_pair("15m / 30m")
    assert prep == 15 and session == 30


def test_parse_format_pair_single():
    prep, session = parse_format_pair("10m")
    assert prep == 10 and session == 0


@pytest.mark.parametrize("raw,n", [("4", 4), ("6 year", 6), (8, 8)])
def test_parse_year(raw, n):
    assert parse_year(raw) == n


def test_parse_date():
    assert parse_date("2024-06-15") == date(2024, 6, 15)


def test_parse_datetime():
    dt = parse_datetime("2024-06-15T12:00:00+00:00")
    assert dt.year == 2024


def test_format_duration():
    assert format_duration(90)


def test_format_year():
    assert format_year(4) == "4 year"


def test_try_parse_date():
    assert try_parse_date("2024-01-01") is not None


def test_parse_duration():
    assert parse_duration("PT1H30M") == 90


def test_parse_iso8601_bad():
    with pytest.raises(ParseError):
        parse_duration("P1D")


def test_parse_format_pair_and():
    prep, session = parse_format_pair("10m and 20m")
    assert prep == 10 and session == 20


def test_parse_year_int_bad():
    with pytest.raises(ParseError):
        parse_year(0)


def test_parse_date_bad():
    with pytest.raises(ParseError):
        parse_date("not-a-date")


def test_parse_datetime_bad():
    with pytest.raises(ParseError):
        parse_datetime("bad")


def test_format_duration_hours_only():
    assert format_duration(120) == "2h"


def test_format_year_one():
    assert format_year(1) == "1 serving"


def test_try_parse_date_bad():
    assert try_parse_date("nope") is None


def test_parse_duration_words_only_minutes():
    assert parse_duration("45 min") == 45


def test_parse_year_digit_string():
    assert parse_year("8") == 8


def test_parse_mechanic_line():
    row = parse_mechanic_line("2 cups flour")
    assert row["name"]


def test_parse_duration_words_hours_minutes():
    assert parse_duration("2 hours 15 min") == 135


def test_parse_duration_zero_raises():
    with pytest.raises(ParseError):
        parse_duration("0h")


def test_parse_year_zero_string():
    with pytest.raises(ParseError):
        parse_year("0")


def test_parse_date_invalid_calendar():
    with pytest.raises(ParseError):
        parse_date("2024-02-30")


def test_format_duration_under_hour():
    assert format_duration(45) == "45m"


def test_parse_quantity_wrapper():
    q = parse_quantity("1.5")
    assert q.value == 1.5


def test_parse_iso8601_zero_duration():
    with pytest.raises(ParseError):
        parse_duration("PT0M")
