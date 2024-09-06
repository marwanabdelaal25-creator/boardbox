"""Tests for io_csv."""
import pytest

from boardbox.errors import ExportError, ImportPipelineError
from boardbox.io_csv import (
    export_games_csv,
    export_wishlist_csv,
    import_games_csv,
    import_wishlist_csv,
    _encode_mechanics,
    _parse_mechanic_line,
    _split_list,
    _componentlist_to_dicts,
)
from tests.helpers import make_game


def test_export_import_roundtrip(empty_storage, tmp_path, sample_games_csv):
    src = tmp_path / "in.csv"
    src.write_text(sample_games_csv, encoding="utf-8")
    n = import_games_csv(empty_storage, src)
    assert n >= 1
    dest = tmp_path / "out.csv"
    export_games_csv(empty_storage, dest)
    assert dest.exists()


def test_import_update_mode(empty_storage, tmp_path, sample_games_csv):
    src = tmp_path / "in.csv"
    src.write_text(sample_games_csv, encoding="utf-8")
    import_games_csv(empty_storage, src)
    n = import_games_csv(empty_storage, src, update=True)
    assert n >= 1


def test_import_missing_file(empty_storage, tmp_path):
    with pytest.raises(ImportPipelineError):
        import_games_csv(empty_storage, tmp_path / "nope.csv")


def test_import_bad_csv(empty_storage, tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("not,enough\n", encoding="utf-8")
    with pytest.raises(ImportPipelineError):
        import_games_csv(empty_storage, bad)


def test_import_wishlist(empty_storage, tmp_path, sample_wishlist_csv):
    src = tmp_path / "shop.csv"
    src.write_text(sample_wishlist_csv, encoding="utf-8")
    n = import_wishlist_csv(empty_storage, src)
    assert n == 1


def test_import_wishlist_missing_column(empty_storage, tmp_path):
    src = tmp_path / "shop.csv"
    src.write_text("qty,unit\n1,cup\n", encoding="utf-8")
    with pytest.raises(ImportPipelineError):
        import_wishlist_csv(empty_storage, src)


def test_export_wishlist(populated_storage, tmp_path):
    dest = tmp_path / "shop_out.csv"
    n = export_wishlist_csv(populated_storage, dest, list_id="weekly")
    assert n >= 0
    assert dest.exists()


def test_encode_mechanics():
    r = make_game()
    text = _encode_mechanics(r)
    assert " ;; " in text or r.mechanics[0].name in text


def test_parse_mechanic_line_variants():
    ing = _parse_mechanic_line("2 cup flour")
    assert ing.name == "flour"
    ing2 = _parse_mechanic_line("salt (optional)")
    assert "optional" in ing2.notes.lower()


def test_split_list_and_componentlist():
    assert _split_list("a | b") == ["a", "b"]
    assert _split_list("") == []
    componentlist = _componentlist_to_dicts(["Mix", ""])
    assert componentlist[0]["text"] == "Mix"


def test_import_single_step_column(empty_storage, tmp_path):
    csv_text = (
        "title,year,publisher_name,format,mechanics,componentlist,source_url,tags\n"
        "Solo,2,,,salt ;; 1 ;; ;;,Just session,,"
    )
    src = tmp_path / "solo.csv"
    src.write_text(csv_text, encoding="utf-8")
    assert import_games_csv(empty_storage, src) == 1


def test_import_missing_file(empty_storage, tmp_path):
    with pytest.raises(ImportPipelineError):
        import_games_csv(empty_storage, tmp_path / "nope.csv")


def test_import_by_id(empty_storage, tmp_path):
    csv_text = (
        "id,title,year,publisher_name,format,mechanics,componentlist,source_url,tags\n"
        "fixed-id,Soup,4,,,water ;; 2 cup ;; ;;,Boil,,"
    )
    src = tmp_path / "id.csv"
    src.write_text(csv_text, encoding="utf-8")
    import_games_csv(empty_storage, src)
    assert empty_storage.get_game("fixed-id").title == "Soup"


def test_import_read_os_error(empty_storage, tmp_path, monkeypatch):
    p = tmp_path / "x.csv"
    p.write_text("title\nX\n", encoding="utf-8")

    def boom(self, *args, **kwargs):
        raise OSError("denied")

    monkeypatch.setattr(type(p), "read_text", boom)
    with pytest.raises(ImportPipelineError):
        import_games_csv(empty_storage, p)


def test_export_games_os_error(populated_storage, tmp_path, monkeypatch):
    from boardbox.errors import ExportError
    import boardbox.io_csv as mod

    monkeypatch.setattr(mod.Path, "open", lambda *a, **k: (_ for _ in ()).throw(OSError("disk")))
    with pytest.raises(ExportError):
        export_games_csv(populated_storage, tmp_path / "out.csv")


def test_export_wishlist_os_error(populated_storage, tmp_path, monkeypatch):
    from boardbox.errors import ExportError
    import boardbox.io_csv as mod

    monkeypatch.setattr(mod.Path, "open", lambda *a, **k: (_ for _ in ()).throw(OSError("disk")))
    with pytest.raises(ExportError):
        export_wishlist_csv(populated_storage, tmp_path / "shop.csv")


def test_import_skips_blank_title(empty_storage, tmp_path):
    csv_text = "title,year,mechanics,componentlist\n,2,salt ;; 1 ;; ;;,Session\nGood,2,salt ;; 1 ;; ;;,Session\n"
    src = tmp_path / "blank.csv"
    src.write_text(csv_text, encoding="utf-8")
    assert import_games_csv(empty_storage, src) == 1


def test_import_update_by_title(populated_storage, tmp_path):
    csv_text = "title,year,mechanics,componentlist\nSunday Pasta,6,salt ;; 1 ;; ;;,New step\n"
    src = tmp_path / "upd.csv"
    src.write_text(csv_text, encoding="utf-8")
    assert import_games_csv(populated_storage, src, update=True) == 1


def test_import_single_step_field(empty_storage, tmp_path):
    csv_text = "title,year,mechanics,componentlist\nOne,2,salt ;; 1 ;; ;;,Only step here\n"
    src = tmp_path / "one.csv"
    src.write_text(csv_text, encoding="utf-8")
    assert import_games_csv(empty_storage, src) == 1


def test_import_single_mechanic_field(empty_storage, tmp_path):
    csv_text = "title,year,mechanics,componentlist\nOne,2,2 cups flour,Mix\n"
    src = tmp_path / "ing.csv"
    src.write_text(csv_text, encoding="utf-8")
    assert import_games_csv(empty_storage, src) == 1


def test_import_validation_error_line(empty_storage, tmp_path, monkeypatch):
    import boardbox.io_csv as mod

    csv_text = "title,year,mechanics,componentlist\nBad,not-int,salt ;; 1 ;; ;;,Session\n"
    src = tmp_path / "bad.csv"
    src.write_text(csv_text, encoding="utf-8")
    with pytest.raises(ImportPipelineError):
        import_games_csv(empty_storage, src)


def test_import_wishlist_skips_blank(empty_storage, tmp_path):
    csv_text = "name,quantity,unit\n,1,cup\nflour,2,cup\n"
    src = tmp_path / "shop.csv"
    src.write_text(csv_text, encoding="utf-8")
    assert import_wishlist_csv(empty_storage, src) == 1


def test_import_wishlist_bad_quantity(empty_storage, tmp_path, monkeypatch):
    import boardbox.io_csv as mod

    csv_text = "name,quantity,unit\nflour,2,cup\n"
    src = tmp_path / "badq.csv"
    src.write_text(csv_text, encoding="utf-8")

    def boom(x):
        raise ValueError("bad quantity")

    monkeypatch.setattr(mod, "parse_quantity", boom)
    with pytest.raises(ImportPipelineError):
        import_wishlist_csv(empty_storage, src)
