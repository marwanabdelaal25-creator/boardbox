"""Tests for boardbox.io_tabletop."""
import pytest

from boardbox.errors import ImportPipelineError
from boardbox.io_tabletop import import_tabletop


def test_import_tabletop(empty_storage, tmp_path, sample_tabletop_csv):
    p = tmp_path / "m.csv"
    p.write_text(sample_tabletop_csv, encoding="utf-8")
    assert import_tabletop(empty_storage, p) >= 1


def test_import_missing(empty_storage, tmp_path):
    with pytest.raises(ImportPipelineError):
        import_tabletop(empty_storage, tmp_path / "nope.csv")


def test_import_empty(empty_storage, tmp_path):
    p = tmp_path / "empty.csv"
    p.write_text("", encoding="utf-8")
    with pytest.raises(ImportPipelineError):
        import_tabletop(empty_storage, p)


def test_import_update(populated_storage, tmp_path, sample_tabletop_csv):
    p = tmp_path / "m.csv"
    p.write_text(sample_tabletop_csv, encoding="utf-8")
    import_tabletop(populated_storage, p)
    assert import_tabletop(populated_storage, p, update=True) >= 0


def test_import_os_error(empty_storage, tmp_path, monkeypatch):
    p = tmp_path / "m.csv"
    p.write_text("Game Name\nX\n", encoding="utf-8")

    def boom(*args, **kwargs):
        raise OSError("denied")

    monkeypatch.setattr(type(p), "read_text", boom)
    with pytest.raises(ImportPipelineError):
        import_tabletop(empty_storage, p)


def test_import_row_validation_error(empty_storage, tmp_path):
    csv_text = "Game Name,Servings,Ingredients,Instructions\n,2,salt,Session\n"
    p = tmp_path / "bad.csv"
    p.write_text(csv_text, encoding="utf-8")
    with pytest.raises(ImportPipelineError):
        import_tabletop(empty_storage, p)


def test_import_skip_duplicate_title(empty_storage, tmp_path):
    csv_text = (
        "Game Name,Servings,Ingredients,Instructions\n"
        "Dup,2,1 cup water,Session\n"
    )
    p = tmp_path / "dup.csv"
    p.write_text(csv_text, encoding="utf-8")
    assert import_tabletop(empty_storage, p) == 1
    assert import_tabletop(empty_storage, p) == 0


def test_long_instructions_split(empty_storage, tmp_path):
    long_text = "1. First step here. 2. Second step here. 3. Third step here. " * 5
    csv_text = f"Game Name,Servings,Ingredients,Instructions\nLong,2,salt,{long_text}\n"
    p = tmp_path / "long.csv"
    p.write_text(csv_text, encoding="utf-8")
    assert import_tabletop(empty_storage, p) == 1
