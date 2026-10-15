"""Load recent GDELT 2.0 events and mentions into the raw layer.

    python -m blindspot.ingest.load_gdelt --hours 24
    python -m blindspot.ingest.load_gdelt --hours 24 --end 20261015193000
"""
import argparse
import logging

import requests

from .backends import make_backend
from .files import download_rows, files_for_window, latest_stamp
from .schema import TABLES

log = logging.getLogger("load_gdelt")


def run(hours: float, kinds: tuple[str, ...], backend=None, session=None, end: str | None = None) -> dict:
    backend = backend or make_backend()
    session = session or requests.Session()
    done = backend.loaded_files()
    stats = {"loaded": 0, "skipped": 0, "missing": 0, "rejected": 0}

    for f in files_for_window(end or latest_stamp(session), hours, kinds):
        if f.name in done:
            stats["skipped"] += 1
            continue
        rows = download_rows(session, f)
        if rows is None:
            log.warning("no file for %s", f.name)
            stats["missing"] += 1
            continue
        table, schema = TABLES[f.kind]
        n, rejected = backend.load(table, schema, rows, f.name)
        stats["loaded"] += 1
        stats["rejected"] += rejected
        log.info("%s: %d rows (%d rejected)", f.name, n, rejected)

    for table, _ in TABLES.values():
        try:
            stats[table] = backend.count(table)
        except Exception:
            stats[table] = 0
    return stats


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--hours", type=float, default=24)
    p.add_argument("--kinds", default="export,mentions")
    p.add_argument("--end", help="last file stamp to load, YYYYMMDDHHMMSS UTC. Pins the window so two runs match")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    print(run(args.hours, tuple(args.kinds.split(",")), end=args.end))


if __name__ == "__main__":
    main()
