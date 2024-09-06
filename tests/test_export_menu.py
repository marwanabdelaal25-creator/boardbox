"""Tests for boardbox.export_menu."""
from datetime import datetime, timezone

from boardbox.export_menu import ExportMenu, WEEKDAYS


def test_build_menu_data_with_plan(populated_storage):
    ex = ExportMenu(populated_storage)
    data = ex.build_menu_data()
    assert data["week_start"]
    assert "Monday" in data["days"]


def test_build_menu_data_no_plan(empty_storage):
    ex = ExportMenu(empty_storage)
    data = ex.build_menu_data()
    assert data["plan_id"] is None


def test_export_text_with_plan(populated_storage):
    ex = ExportMenu(populated_storage)
    txt = ex.export_text()
    assert "Weekly Menu" in txt


def test_export_text_no_plan(empty_storage):
    ex = ExportMenu(empty_storage)
    txt = ex.export_text()
    assert "no meal plan" in txt.lower()


def test_export_markdown_with_plan(populated_storage):
    ex = ExportMenu(populated_storage)
    md = ex.export_markdown()
    assert "# Weekly Menu" in md


def test_export_markdown_no_plan(empty_storage):
    ex = ExportMenu(empty_storage)
    md = ex.export_markdown()
    assert "No meal plan" in md


def test_wishlist_from_menu(populated_storage):
    ex = ExportMenu(populated_storage)
    items = ex.wishlist_from_menu()
    assert isinstance(items, list)


def test_wishlist_from_menu_empty(empty_storage):
    ex = ExportMenu(empty_storage)
    assert ex.wishlist_from_menu() == []


def test_export_wishlist_markdown(populated_storage):
    ex = ExportMenu(populated_storage)
    md = ex.export_wishlist_markdown()
    assert "Shopping List" in md


def test_game_title_fallback(populated_storage):
    ex = ExportMenu(populated_storage)
    assert ex._game_title("missing-id-xyz") == "missing-id-xyz"


def test_days_from_plan_string_entries(populated_storage):
    ex = ExportMenu(populated_storage)
    plan = {"days": {"Monday": ["rec001"]}}
    days = ex._days_from_plan(plan)
    assert days["Monday"]


def test_days_from_plan_dict_entries(populated_storage):
    ex = ExportMenu(populated_storage)
    plan = {"days": {"monday": [{"game_id": "rec001", "meal": "lunch"}]}}
    days = ex._days_from_plan(plan)
    assert any("Sunday Pasta" in t or "rec001" in t for t in days.get("Monday", []))


def test_week_start_fixed_ref(populated_storage):
    ex = ExportMenu(populated_storage)
    ref = datetime(2024, 6, 5, 12, 0, tzinfo=timezone.utc)  # Wednesday
    start = ex._week_start(ref)
    assert start.weekday() == 0


def test_menu_notes_in_export(populated_storage):
    ex = ExportMenu(populated_storage)
    plans = populated_storage.list_campaigns()
    if plans:
        populated_storage.update_night_plan(plans[0]["id"], {"notes": "Test week note"})
    txt = ex.export_text()
    assert isinstance(txt, str)
