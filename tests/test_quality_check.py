import duckdb
import pytest

from blindspot.quality import check


def test_check_fails_loudly_on_empty_warehouse(tmp_path, monkeypatch, capsys):
    db = tmp_path / "empty.duckdb"
    duckdb.connect(str(db)).close()
    monkeypatch.setenv("DUCKDB_PATH", str(db))
    monkeypatch.delenv("DBT_TARGET", raising=False)
    assert check.main() == 1
    assert "Data quality check failed" in capsys.readouterr().err
