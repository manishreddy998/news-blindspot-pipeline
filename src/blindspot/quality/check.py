"""Quick health check on the built tables. Exits with code 1 and a clear list of
problems if anything looks wrong, so a scheduler or CI step stops right there.

    python -m blindspot.quality.check
"""
import os
import sys

# (name, sql returning one number, test, what it means)
CHECKS = [
    ("raw events loaded", "select count(*) from {raw}.raw_gdelt_events", lambda n: n > 0,
     "the loader wrote nothing"),
    ("stories built", "select count(*) from {mart}.stories", lambda n: n > 0,
     "dbt built no stories"),
    ("mentions joined to events", "select avg(case when e.event_id is not null then 1.0 else 0.0 end) "
     "from {mart}.stg_gdelt_mentions m left join {mart}.stg_gdelt_events e on e.event_id = m.event_id",
     lambda x: x >= 0.8, "under 80% of mentions match a loaded event"),
    ("stories with a scored split", "select count(*) from {mart}.story_blindspots where left_share is not null",
     lambda n: n > 0, "no story has rated left or right coverage, check the outlet seed"),
    ("scores out of range", "select count(*) from {mart}.story_blindspots "
     "where blindspot_score < 0 or blindspot_score > 1", lambda n: n == 0, "bad score math"),
    ("syndicated share of articles", "select avg(case when is_syndicated then 1.0 else 0.0 end) "
     "from {mart}.stg_article_copies", lambda x: x < 0.6,
     "most articles look like copies, the copy key is probably too loose"),
]


def _runner():
    if os.getenv("DBT_TARGET", "duckdb") == "bigquery":
        from google.cloud import bigquery

        project = os.environ["GCP_PROJECT"]
        client = bigquery.Client(project=project)
        names = {"raw": f"`{project}.raw_gdelt`", "mart": f"`{project}.analytics`"}

        def run(sql):
            return list(client.query(sql.format(**names)).result())[0][0]
    else:
        import duckdb

        con = duckdb.connect(os.getenv("DUCKDB_PATH", "data/blindspot.duckdb"), read_only=True)
        names = {"raw": "main", "mart": "main"}

        def run(sql):
            return con.execute(sql.format(**names)).fetchone()[0]
    return run


def main() -> int:
    run = _runner()
    failed = []
    for name, sql, ok, meaning in CHECKS:
        try:
            value = run(sql)
        except Exception as exc:  # a missing table is a failure, not a crash
            value, good = f"error: {exc}".splitlines()[0], False
        else:
            good = value is not None and ok(float(value))
        shown = f"{value:.3f}" if isinstance(value, float) else value
        print(f"{'ok  ' if good else 'FAIL'} {name}: {shown}")
        if not good:
            failed.append(f"{name}: {meaning}")
    if failed:
        print("\nData quality check failed:\n  " + "\n  ".join(failed), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
