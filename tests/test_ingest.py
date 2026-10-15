import io
import zipfile

from blindspot.ingest.backends import DuckDBBackend
from blindspot.ingest.files import files_for_window, parse_rows
from blindspot.ingest.load_gdelt import run
from blindspot.ingest.schema import MENTIONS


def test_window_covers_every_slot_oldest_first():
    files = files_for_window("20261015120000", 1, ("export", "mentions"))
    assert [f.name for f in files[:2]] == ["20261015111500.export.CSV.zip", "20261015111500.mentions.CSV.zip"]
    assert files[-1].stamp == "20261015120000"
    assert len(files) == 8


def _mention_row(event_id: int, url: str) -> str:
    vals = [str(event_id), "20261015120000", "20261015120000", "1", "cbc.ca", url,
            "1", "-1", "10", "20", "1", "100", "2500", "-1.5", "", ""]
    assert len(vals) == len(MENTIONS)
    return "\t".join(vals)


class FakeResponse:
    def __init__(self, status, content=b"", text=""):
        self.status_code, self.content, self.text = status, content, text

    def raise_for_status(self):
        assert self.status_code == 200


class FakeSession:
    def __init__(self, body: str):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("x.CSV", body)
        self.zip = buf.getvalue()
        self.calls = 0

    def get(self, url, timeout):
        if url.endswith("lastupdate.txt"):
            return FakeResponse(200, text="1 a https://x/20261015120000.mentions.CSV.zip")
        self.calls += 1
        return FakeResponse(200, content=self.zip)


def test_load_is_idempotent_and_drops_bad_rows(tmp_path):
    body = "\n".join([
        _mention_row(1, "https://cbc.ca/a"),
        _mention_row(2, "https://cbc.ca/b"),
        "short\trow",
        _mention_row(3, "https://cbc.ca/c").replace("\t-1.5\t", "\tnot_a_number\t"),
    ])
    backend = DuckDBBackend(str(tmp_path / "t.duckdb"))
    session = FakeSession(body)

    first = run(0.25, ("mentions",), backend, session)
    assert first["raw_gdelt_mentions"] == 2
    assert first["rejected"] == 2

    second = run(0.25, ("mentions",), backend, session)
    assert second["skipped"] == 1 and second["loaded"] == 0
    assert second["raw_gdelt_mentions"] == 2
    assert session.calls == 1


def test_parse_rows_keeps_empty_fields():
    assert parse_rows("a\t\tc\n\n") == [["a", "", "c"]]
