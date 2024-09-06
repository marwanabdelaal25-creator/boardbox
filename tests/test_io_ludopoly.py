"""Tests for boardbox.io_ludopoly."""
import pytest

from boardbox.errors import ImportPipelineError
from boardbox.io_ludopoly import import_rt


def test_import_rt(empty_storage, tmp_path, sample_sessionmate_csv):
    p = tmp_path / "cm.csv"
    p.write_text(sample_sessionmate_csv, encoding="utf-8")
    assert import_rt(empty_storage, p) >= 1


def test_import_missing(empty_storage, tmp_path):
    with pytest.raises(ImportPipelineError):
        import_rt(empty_storage, tmp_path / "nope.csv")


def test_import_empty(empty_storage, tmp_path):
    p = tmp_path / "empty.csv"
    p.write_text("", encoding="utf-8")
    with pytest.raises(ImportPipelineError):
        import_rt(empty_storage, p)


def test_import_update(populated_storage, tmp_path, sample_sessionmate_csv):
    p = tmp_path / "cm.csv"
    p.write_text(sample_sessionmate_csv, encoding="utf-8")
    import_rt(populated_storage, p)
    assert import_rt(populated_storage, p, update=True) >= 0
