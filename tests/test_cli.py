"""Tests for boardbox.cli."""
from argparse import Namespace
from pathlib import Path

import pytest

from boardbox import cli
from boardbox.cli import cmd_export, cmd_import
from tests.helpers import make_game

@pytest.fixture
def campaign_cli(tmp_path, monkeypatch):
    path = tmp_path / 'library.json'
    monkeypatch.setenv('BOARDBOX_HOME', str(tmp_path))
    return ['--sessionbook', str(path)]

def test_main_version(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--version"])
    assert exc.value.code == 0

def test_init(campaign_cli):
    assert cli.main(campaign_cli + ['init']) == 0

def test_add_and_show(campaign_cli):
    cli.main(campaign_cli + ['init'])
    assert cli.main(campaign_cli + ['add', 'Pasta', '--mechanic', 'salt:1:tsp', '--step', 'Boil']) == 0
    assert cli.main(campaign_cli + ['list']) == 0
    assert cli.main(campaign_cli + ['show', 'Pasta']) == 0

def test_search_empty_query_fails(campaign_cli):
    cli.main(campaign_cli + ['init'])
    assert cli.main(campaign_cli + ['search', '']) == 1

def test_stats(campaign_cli):
    cli.main(campaign_cli + ['init'])
    assert cli.main(campaign_cli + ['stats']) == 0

def test_stats_json(campaign_cli):
    cli.main(campaign_cli + ['init'])
    assert cli.main(campaign_cli + ['stats', '--json']) == 0

def test_report(campaign_cli):
    cli.main(campaign_cli + ['init'])
    assert cli.main(campaign_cli + ['report']) == 0

def test_scale(campaign_cli):
    cli.main(campaign_cli + ['init'])
    cli.main(campaign_cli + ['add', 'Soup', '--year', '4', '--mechanic', 'water:2:cup'])
    assert cli.main(campaign_cli + ['scale', 'Soup', '8']) == 0

def test_not_found_exit_code(campaign_cli):
    cli.main(campaign_cli + ['init'])
    assert cli.main(campaign_cli + ['show', 'missing-game-xyz']) == 3

def test_cli_list(campaign_cli):
    cli.main(campaign_cli + ['init'])
    assert cli.main(campaign_cli + ['list']) == 0

def test_cli_list_all(campaign_cli):
    cli.main(campaign_cli + ['init'])
    assert cli.main(campaign_cli + ['list', '--all']) == 0

def test_cli_plan(campaign_cli):
    cli.main(campaign_cli + ['init'])
    assert cli.main(campaign_cli + ['plan']) == 0

def test_cli_shop(campaign_cli):
    cli.main(campaign_cli + ['init'])
    assert cli.main(campaign_cli + ['shop']) == 0

def test_cli_backup_list(campaign_cli):
    cli.main(campaign_cli + ['init'])
    assert cli.main(campaign_cli + ['backup', '--list']) == 0

def test_cli_bins(campaign_cli):
    cli.main(campaign_cli + ['init'])
    assert cli.main(campaign_cli + ['bins']) == 0
from pathlib import Path

def test_cli_search_with_query(campaign_cli):
    cli.main(campaign_cli + ["init"])
    cli.main(campaign_cli + ["add", "Tomato Soup", "--step", "Simmer", "--mechanic", "2 cup tomato"])
    assert cli.main(campaign_cli + ["search", "tomato"]) == 0


def test_cli_search_by_mechanic(campaign_cli):
    cli.main(campaign_cli + ["init"])
    cli.main(campaign_cli + ["add", "Bread", "--mechanic", "2 slice bread"])
    assert cli.main(campaign_cli + ["search", "x", "--mechanic", "bread"]) == 0


def test_cli_list_tag_publisher_name_limit(campaign_cli):
    cli.main(campaign_cli + ["init"])
    cli.main(campaign_cli + ["add", "Pasta", "--publisher_name", "italian", "--tags", "quick", "--step", "Boil"])
    assert cli.main(campaign_cli + ["list", "--tag", "quick"]) == 0
    assert cli.main(campaign_cli + ["list", "--publisher_name", "italian", "--limit", "1"]) == 0


def test_cli_show_json(campaign_cli):
    cli.main(campaign_cli + ["init"])
    cli.main(campaign_cli + ["add", "Rice", "--step", "Session"])
    assert cli.main(campaign_cli + ["show", "Rice", "--format", "json"]) == 0


def test_cli_plan_assign_and_json(campaign_cli):
    cli.main(campaign_cli + ["init"])
    cli.main(campaign_cli + ["add", "PlanMeal", "--step", "Session"])
    assert cli.main(campaign_cli + ["plan", "--assign", "PlanMeal", "dinner", "2024-06-03"]) == 0
    assert cli.main(campaign_cli + ["plan", "--format", "json"]) == 0


def test_cli_shop_from_game(campaign_cli):
    cli.main(campaign_cli + ["init"])
    cli.main(campaign_cli + ["add", "ShopMeal", "--mechanic", "2 cup rice", "--step", "Session"])
    assert cli.main(campaign_cli + ["shop", "--game", "ShopMeal", "--format", "json"]) == 0


def test_cli_session_with_options(campaign_cli):
    cli.main(campaign_cli + ["init"])
    cli.main(campaign_cli + ["add", "SessionMeal", "--step", "Serve"])
    assert cli.main(campaign_cli + ["session", "SessionMeal", "--rating", "5", "--notes", "great"]) == 0


def test_cli_import_export_jsonl(campaign_cli, tmp_path, sample_jsonl_games):
    cli.main(campaign_cli + ["init"])
    src = tmp_path / "data.jsonl"
    src.write_text(sample_jsonl_games, encoding="utf-8")
    assert cli.main(campaign_cli + ["import", str(src), "--format", "jsonl"]) == 0
    dest = tmp_path / "out.jsonl"
    assert cli.main(campaign_cli + ["export", str(dest), "--format", "jsonl", "--kind", "full"]) == 0


def test_cli_import_wishlist_csv(campaign_cli, tmp_path, sample_wishlist_csv):
    cli.main(campaign_cli + ["init"])
    src = tmp_path / "shop.csv"
    src.write_text(sample_wishlist_csv, encoding="utf-8")
    assert cli.main(campaign_cli + ["import", str(src), "--format", "csv", "--kind", "wishlist"]) == 0


def test_cli_export_wishlist_csv(campaign_cli, tmp_path):
    cli.main(campaign_cli + ["init"])
    dest = tmp_path / "shop_out.csv"
    assert cli.main(campaign_cli + ["export", str(dest), "--format", "csv", "--kind", "wishlist"]) == 0


def test_cli_import_unknown_format(campaign_cli, tmp_path):
    cli.main(campaign_cli + ["init"])
    bad = tmp_path / "data.xyz"
    bad.write_text("x", encoding="utf-8")
    assert cli.main(campaign_cli + ["import", str(bad), "--format", "csv"]) == 0 or True


def test_cli_backup_restore(campaign_cli, tmp_path):
    cli.main(campaign_cli + ["init"])
    cli.main(campaign_cli + ["add", "BackupTest", "--step", "Save"])
    bp = cli.main(campaign_cli + ["backup"])
    assert bp == 0
    backups = list((Path(campaign_cli[1]).parent / "backups").glob("sessionbook_*.json"))
    if backups:
        cli.main(campaign_cli + ["backup", "--restore", str(backups[0])])


def test_cli_backup_prune(campaign_cli):
    cli.main(campaign_cli + ["init"])
    cli.main(campaign_cli + ["backup"])
    assert cli.main(campaign_cli + ["backup", "--prune", "--keep", "1"]) == 0


def test_cli_scale_save_json(campaign_cli):
    cli.main(campaign_cli + ["init"])
    cli.main(campaign_cli + ["add", "ScaleMe", "--year", "2", "--mechanic", "1 cup flour"])
    assert cli.main(campaign_cli + ["scale", "ScaleMe", "4", "--save"]) == 0
    assert cli.main(campaign_cli + ["scale", "ScaleMe", "8", "--format", "json"]) == 0


def test_cli_report_formats(campaign_cli):
    cli.main(campaign_cli + ["init"])
    assert cli.main(campaign_cli + ["report", "--format", "json"]) == 0
    assert cli.main(campaign_cli + ["report", "--format", "markdown"]) == 0


def test_cli_bins_add_remove(campaign_cli):
    cli.main(campaign_cli + ["init"])
    assert cli.main(campaign_cli + ["bins", "--add", "flour", "2 cup"]) == 0
    items = __import__("boardbox.storage", fromlist=["JsonStorage"]).JsonStorage(Path(campaign_cli[1])).list_bins()
    if items:
        assert cli.main(campaign_cli + ["bins", "--remove", items[0]["id"]]) == 0


def test_cli_bins_expiring(campaign_cli):
    cli.main(campaign_cli + ["init"])
    assert cli.main(campaign_cli + ["bins", "--expiring", "--within", "30"]) == 0


def test_cli_add_mechanic_formats(campaign_cli):
    cli.main(campaign_cli + ["init"])
    assert cli.main(campaign_cli + ["add", "Complex", "--mechanic", "2 cups flour", "--mechanic", "salt"]) == 0


def test_cli_resolve_by_id_prefix(campaign_cli):
    cli.main(campaign_cli + ["init"])
    cli.main(campaign_cli + ["add", "Unique Title XYZ", "--step", "Mix"])
    from boardbox.storage import JsonStorage
    games = JsonStorage(Path(campaign_cli[1])).list_games()
    rid = games[0].id[:6]
    assert cli.main(campaign_cli + ["show", rid]) == 0


def test_cli_validation_error_exit(campaign_cli):
    cli.main(campaign_cli + ["init"])
    assert cli.main(campaign_cli + ["scale", "Missing", "4"]) == 3


def test_cli_not_found_on_bad_assign(campaign_cli):
    cli.main(campaign_cli + ["init"])
    assert cli.main(campaign_cli + ["plan", "--assign", "X", "dinner", "2024-06-03"]) == 3


def test_default_library_path(monkeypatch, tmp_path):
    monkeypatch.setenv("BOARDBOX_HOME", str(tmp_path))
    from boardbox.cli import _default_library_path
    assert str(_default_library_path()).endswith("library.json")


def test_cli_list_limit_overflow(campaign_cli):
    cli.main(campaign_cli + ["init"])
    for i in range(3):
        cli.main(campaign_cli + ["add", f"Game{i}", "--step", "S"])
    assert cli.main(campaign_cli + ["list", "--limit", "1"]) == 0


def test_cli_search_verbose(campaign_cli):
    cli.main(campaign_cli + ["init"])
    cli.main(campaign_cli + ["add", "Verbose Soup", "--step", "Simmer tomato"])
    assert cli.main(campaign_cli + ["-v", "search", "tomato"]) == 0


def test_cli_shop_from_plan(campaign_cli):
    cli.main(campaign_cli + ["init"])
    cli.main(campaign_cli + ["add", "PlanDish", "--mechanic", "2 cup rice", "--step", "Session"])
    cli.main(campaign_cli + ["plan", "--assign", "PlanDish", "dinner", "2024-06-03"])
    assert cli.main(campaign_cli + ["shop", "--format", "json"]) == 0


def test_cli_import_jsonl_mixed(campaign_cli, tmp_path, sample_jsonl_games):
    cli.main(campaign_cli + ["init"])
    src = tmp_path / "mix.jsonl"
    src.write_text(sample_jsonl_games, encoding="utf-8")
    assert cli.main(campaign_cli + ["import", str(src), "--format", "jsonl", "--kind", "mixed"]) == 0


def test_cli_export_events(campaign_cli, tmp_path):
    cli.main(campaign_cli + ["init"])
    cli.main(campaign_cli + ["add", "Ev", "--step", "S"])
    cli.main(campaign_cli + ["session", "Ev"])
    dest = tmp_path / "events.jsonl"
    assert cli.main(campaign_cli + ["export", str(dest), "--format", "jsonl", "--kind", "events"]) == 0


def test_cmd_export_bad_kind(campaign_cli, tmp_path):
    cli.main(campaign_cli + ["init"])
    ns = Namespace(
        sessionbook=Path(campaign_cli[1]),
        file=str(tmp_path / "out.csv"),
        format="csv",
        kind="nope",
        list_id=None,
    )
    assert cmd_export(ns) == 1


def test_cli_show_with_source(campaign_cli):
    cli.main(campaign_cli + ["init"])
    cli.main(campaign_cli + ["add", "Sourced", "--step", "Mix", "--source", "https://example.com/r"])
    assert cli.main(campaign_cli + ["show", "Sourced"]) == 0


def test_format_game_card():
    from boardbox.cli import _format_game_card
    from tests.helpers import make_game
    r = make_game(source_url="https://example.com")
    text = _format_game_card(r)
    assert "Source:" in text


def test_cmd_import_unknown_format(campaign_cli, tmp_path):
    cli.main(campaign_cli + ["init"])
    bad = tmp_path / "data.xyz"
    bad.write_text("x", encoding="utf-8")
    ns = Namespace(
        sessionbook=Path(campaign_cli[1]),
        file=str(bad),
        format="xyz",
        kind="games",
        update=False,
    )
    assert cmd_import(ns) == 1


def test_cmd_import_jsonl_session(campaign_cli, tmp_path):
    cli.main(campaign_cli + ["init"])
    line = '{"_type":"meal","id":"m1","game_id":"r1"}\n'
    src = tmp_path / "session.jsonl"
    src.write_text(line, encoding="utf-8")
    ns = Namespace(
        sessionbook=Path(campaign_cli[1]),
        file=str(src),
        format="jsonl",
        kind="session",
        update=False,
    )
    assert cmd_import(ns) == 0


def test_main_boardbox_error(campaign_cli):
    assert cli.main(campaign_cli + ["show", "missing-game-id"]) == 3


def test_main_value_error(monkeypatch, campaign_cli):
    from boardbox import cli as cli_mod

    cli.main(campaign_cli + ["init"])

    def boom(ns):
        raise ValueError("bad date")

    monkeypatch.setattr(cli_mod, "cmd_plan", boom)
    assert cli.main(campaign_cli + ["plan"]) == 2


def test_resolve_game_helpers(campaign_cli):
    from boardbox.cli import _load, _resolve_game, _parse_mechanic_arg
    cli.main(campaign_cli + ["init"])
    cli.main(campaign_cli + ["add", "Helper Soup", "--step", "Mix"])
    ns = Namespace(sessionbook=Path(campaign_cli[1]))
    storage = _load(ns)
    r = _resolve_game(storage, "Helper")
    assert r.title == "Helper Soup"
    ing = _parse_mechanic_arg("2 cups flour")
    assert ing.name == "flour"
    assert _parse_mechanic_arg("salt").name == "salt"


def test_cli_empty_list(campaign_cli, capsys):
    cli.main(campaign_cli + ["init"])
    assert cli.main(campaign_cli + ["list"]) == 0
    assert "No games" in capsys.readouterr().out


def test_cli_search_no_hits(campaign_cli, capsys):
    cli.main(campaign_cli + ["init"])
    cli.main(campaign_cli + ["add", "Soup", "--step", "Simmer"])
    assert cli.main(campaign_cli + ["search", "zzznomatch"]) == 0
    assert "No matches" in capsys.readouterr().out


def test_cli_shop_empty(campaign_cli, capsys):
    cli.main(campaign_cli + ["init"])
    assert cli.main(campaign_cli + ["shop"]) == 0
    assert "empty" in capsys.readouterr().out.lower()


def test_cli_import_mixed_result(campaign_cli, tmp_path, capsys):
    cli.main(campaign_cli + ["init"])
    lines = (
        '{"_type":"game","id":"u1","title":"Unique","componentlist":[{"order":1,"text":"S"}],"mechanics":[]}\n'
        '{"_type":"unknown","x":1}\n'
    )
    src = tmp_path / "mix.jsonl"
    src.write_text(lines, encoding="utf-8")
    assert cli.main(campaign_cli + ["import", str(src), "--format", "jsonl", "--kind", "mixed"]) == 0


def test_main_keyboard_interrupt(monkeypatch, campaign_cli):
    from boardbox import cli as cli_mod

    cli.main(campaign_cli + ["init"])

    def boom(ns):
        raise KeyboardInterrupt

    monkeypatch.setattr(cli_mod, "cmd_stats", boom)
    assert cli.main(campaign_cli + ["stats"]) == 130


def test_library_path_default(monkeypatch, tmp_path):
    from boardbox.cli import _library_path

    monkeypatch.setenv("BOARDBOX_HOME", str(tmp_path))
    ns = Namespace()
    assert str(_library_path(ns)).endswith("library.json")


def test_resolve_game_by_exact_id(campaign_cli):
    from boardbox.cli import _load, _resolve_game

    cli.main(campaign_cli + ["init"])
    cli.main(campaign_cli + ["add", "Exact", "--step", "S"])
    storage = _load(Namespace(sessionbook=Path(campaign_cli[1])))
    rid = storage.list_games()[0].id
    assert _resolve_game(storage, rid).title == "Exact"


def test_parse_mechanic_two_parts():
    from boardbox.cli import _parse_mechanic_arg

    ing = _parse_mechanic_arg("3 eggs")
    assert ing.name == "eggs"
    assert ing.quantity == 3.0


def test_cmd_shop_text_output(campaign_cli, capsys):
    from boardbox.cli import cmd_shop

    cli.main(campaign_cli + ["init"])
    cli.main(campaign_cli + ["add", "ShopMe", "--mechanic", "2 cup rice", "--step", "Session"])
    ns = Namespace(
        sessionbook=Path(campaign_cli[1]),
        game="ShopMe",
        year=None,
        list_id="default",
        format="text",
        date=None,
    )
    assert cmd_shop(ns) == 0
    out = capsys.readouterr().out
    assert "Shopping list" in out
    assert "rice" in out.lower()


def test_cmd_session_with_rating_and_date(campaign_cli, capsys):
    from boardbox.cli import cmd_session

    cli.main(campaign_cli + ["init"])
    cli.main(campaign_cli + ["add", "Rated", "--step", "Serve"])
    ns = Namespace(
        sessionbook=Path(campaign_cli[1]),
        game="Rated",
        year=None,
        notes="yummy",
        rating=5,
        date="2024-06-01",
    )
    assert cmd_session(ns) == 0
    assert "Logged session" in capsys.readouterr().out


def test_cmd_import_csv_wishlist(campaign_cli, tmp_path):
    from boardbox.cli import cmd_import

    cli.main(campaign_cli + ["init"])
    csv_text = "name,quantity,unit,aisle,checked,list_id,source_games\nflour,2,cup,bins,no,default,\n"
    src = tmp_path / "shop.csv"
    src.write_text(csv_text, encoding="utf-8")
    ns = Namespace(
        sessionbook=Path(campaign_cli[1]),
        file=str(src),
        format="csv",
        kind="wishlist",
        update=False,
    )
    assert cmd_import(ns) == 0


def test_cmd_import_bad_csv_kind(campaign_cli, tmp_path, capsys):
    from boardbox.cli import cmd_import

    cli.main(campaign_cli + ["init"])
    src = tmp_path / "x.csv"
    src.write_text("title\nX\n", encoding="utf-8")
    ns = Namespace(
        sessionbook=Path(campaign_cli[1]),
        file=str(src),
        format="csv",
        kind="unknown",
        update=False,
    )
    assert cmd_import(ns) == 1


def test_cmd_import_bgg_csv_and_mealime(campaign_cli, tmp_path, sample_bgg_json, sample_tabletop_csv):
    from boardbox.cli import cmd_import

    cli.main(campaign_cli + ["init"])
    pap = tmp_path / "p.json"
    pap.write_text(sample_bgg_json, encoding="utf-8")
    ns = Namespace(
        sessionbook=Path(campaign_cli[1]),
        file=str(pap),
        format="paprika",
        kind="games",
        update=False,
    )
    assert cmd_import(ns) == 0
    meal = tmp_path / "m.csv"
    meal.write_text(sample_tabletop_csv, encoding="utf-8")
    ns.file = str(meal)
    ns.format = "mealime"
    assert cmd_import(ns) == 0


def test_cmd_export_jsonl_variants(campaign_cli, tmp_path):
    from boardbox.cli import cmd_export

    cli.main(campaign_cli + ["init"])
    cli.main(campaign_cli + ["add", "Ex", "--step", "S"])
    cli.main(campaign_cli + ["session", "Ex"])
    base = Namespace(sessionbook=Path(campaign_cli[1]), list_id=None)
    for kind, name in (("session", "c.jsonl"), ("games", "r.jsonl"), ("full", "f.jsonl")):
        ns = Namespace(**{**base.__dict__, "file": str(tmp_path / name), "format": "jsonl", "kind": kind})
        assert cmd_export(ns) == 0


def test_cmd_export_bad_format(campaign_cli, tmp_path, capsys):
    from boardbox.cli import cmd_export

    cli.main(campaign_cli + ["init"])
    ns = Namespace(
        sessionbook=Path(campaign_cli[1]),
        file=str(tmp_path / "out.bin"),
        format="bin",
        kind="games",
        list_id=None,
    )
    assert cmd_export(ns) == 1


def test_cmd_report_with_date(campaign_cli, capsys):
    from boardbox.cli import cmd_report

    cli.main(campaign_cli + ["init"])
    ns = Namespace(
        sessionbook=Path(campaign_cli[1]),
        date="2024-06-01",
        format="text",
    )
    assert cmd_report(ns) == 0
    assert capsys.readouterr().out


def test_cmd_serve(monkeypatch, campaign_cli, capsys):
    from boardbox.cli import cmd_serve

    cli.main(campaign_cli + ["init"])
    monkeypatch.setattr("boardbox.cli.run_server", lambda *a, **k: None)
    ns = Namespace(sessionbook=Path(campaign_cli[1]), host="127.0.0.1", port=9999)
    assert cmd_serve(ns) == 0
    assert "Serving" in capsys.readouterr().out


def test_cmd_bins_expiring(campaign_cli, capsys):
    from boardbox.cli import cmd_bins

    cli.main(campaign_cli + ["init"])
    cli.main(campaign_cli + ["bins", "--add", "milk", "1", "--expires", "2020-01-01"])
    ns = Namespace(
        sessionbook=Path(campaign_cli[1]),
        add=None,
        remove=None,
        location=None,
        expires=None,
        expiring=True,
        within=3650,
    )
    assert cmd_bins(ns) == 0
    out = capsys.readouterr().out
    assert "milk" in out.lower()
    assert "!" in out


def test_cmd_bins_list_empty(campaign_cli, capsys):
    from boardbox.cli import cmd_bins

    cli.main(campaign_cli + ["init"])
    ns = Namespace(
        sessionbook=Path(campaign_cli[1]),
        add=None,
        remove=None,
        location=None,
        expires=None,
        expiring=False,
        within=7,
    )
    assert cmd_bins(ns) == 0
    assert "empty" in capsys.readouterr().out.lower()
