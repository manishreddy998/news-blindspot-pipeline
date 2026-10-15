"""Find and download GDELT 2.0 15 minute export files."""
import io
import re
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import requests

# Plain http on data.gdeltproject.org times out from some networks, https works.
BASE_URL = "https://data.gdeltproject.org/gdeltv2"
FILE_RE = re.compile(r"(\d{14})\.(export|mentions)\.CSV\.zip$")


@dataclass(frozen=True)
class GdeltFile:
    stamp: str  # YYYYMMDDHHMMSS, UTC
    kind: str  # "export" or "mentions"

    @property
    def name(self) -> str:
        return f"{self.stamp}.{self.kind}.CSV.zip"

    @property
    def url(self) -> str:
        return f"{BASE_URL}/{self.name}"


def latest_stamp(session: requests.Session) -> str:
    text = session.get(f"{BASE_URL}/lastupdate.txt", timeout=30).text
    for line in text.splitlines():
        m = FILE_RE.search(line)
        if m:
            return m.group(1)
    raise RuntimeError("could not parse lastupdate.txt")


def files_for_window(latest: str, hours: float, kinds: tuple[str, ...]) -> list[GdeltFile]:
    """Every 15 minute slot from `latest` back `hours` hours, oldest first.

    Building the list from timestamps avoids pulling masterfilelist.txt,
    which is several hundred MB.
    """
    end = datetime.strptime(latest, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
    slots = int(hours * 4)
    stamps = [(end - timedelta(minutes=15 * i)).strftime("%Y%m%d%H%M%S") for i in range(slots)]
    return [GdeltFile(s, k) for s in reversed(stamps) for k in kinds]


def download_rows(session: requests.Session, f: GdeltFile) -> list[list[str]] | None:
    """Return the tab separated rows of one file, or None if GDELT skipped that slot."""
    resp = session.get(f.url, timeout=60)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        raw = zf.read(zf.namelist()[0]).decode("utf-8", errors="replace")
    return parse_rows(raw)


def parse_rows(raw: str) -> list[list[str]]:
    # GDELT fields are never quoted, so a plain split is safer than the csv module.
    return [line.split("\t") for line in raw.splitlines() if line]
