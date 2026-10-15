"""Where raw rows land. DuckDB for local runs, BigQuery once a GCP project exists."""
import csv
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .schema import DUCKDB_TYPES, LINEAGE

MANIFEST = "_load_manifest"


def _write_tsv(rows: list[list[str]], source_file: str, ncols: int) -> Path:
    tmp = tempfile.NamedTemporaryFile("w", suffix=".tsv", delete=False, newline="", encoding="utf-8")
    w = csv.writer(tmp, delimiter="\t", quoting=csv.QUOTE_NONE, escapechar="\\", lineterminator="\n")
    for r in rows:
        w.writerow([*r[:ncols], source_file])
    tmp.close()
    return Path(tmp.name)


class DuckDBBackend:
    def __init__(self, path: str):
        import duckdb

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.con = duckdb.connect(path)
        self.con.execute(
            f"CREATE TABLE IF NOT EXISTS {MANIFEST} ("
            "file_name VARCHAR PRIMARY KEY, table_name VARCHAR, row_count BIGINT, "
            "rejected_rows BIGINT, loaded_at TIMESTAMP)"
        )

    def loaded_files(self) -> set[str]:
        return {r[0] for r in self.con.execute(f"SELECT file_name FROM {MANIFEST}").fetchall()}

    def load(self, table: str, schema, rows, source_file: str) -> tuple[int, int]:
        cols = schema + LINEAGE
        ddl = ", ".join(f'"{n}" {DUCKDB_TYPES[t]}' for n, t in cols)
        self.con.execute(f"CREATE TABLE IF NOT EXISTS {table} ({ddl})")
        good = [r for r in rows if len(r) == len(schema)]
        tsv = _write_tsv(good, source_file, len(schema))
        col_spec = "{" + ", ".join(f"'{n}': '{DUCKDB_TYPES[t]}'" for n, t in cols) + "}"
        try:
            self.con.begin()
            # Delete first so a file that half loaded before is replaced, not doubled.
            self.con.execute(f"DELETE FROM {table} WHERE source_file = ?", [source_file])
            self.con.execute(
                f"INSERT INTO {table} SELECT * FROM read_csv(?, delim='\t', header=false, "
                f"quote='', escape='\\', columns={col_spec}, ignore_errors=true)",
                [str(tsv)],
            )
            n = self.con.execute(f"SELECT count(*) FROM {table} WHERE source_file = ?", [source_file]).fetchone()[0]
            rejected = len(rows) - n
            self.con.execute(
                f"INSERT OR REPLACE INTO {MANIFEST} VALUES (?, ?, ?, ?, ?)",
                [source_file, table, n, rejected, datetime.now(timezone.utc)],
            )
            self.con.commit()
        except Exception:
            self.con.rollback()
            raise
        finally:
            tsv.unlink(missing_ok=True)
        return n, rejected

    def count(self, table: str) -> int:
        return self.con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]


class BigQueryBackend:
    """Same contract as DuckDBBackend. Not exercised until credentials exist."""

    def __init__(self, project: str, dataset: str, location: str = "US"):
        from google.cloud import bigquery

        self.bq = bigquery
        self.client = bigquery.Client(project=project)
        self.dataset = f"{project}.{dataset}"
        self.client.create_dataset(bigquery.Dataset(self.dataset), exists_ok=True)
        self.manifest = f"{self.dataset}.{MANIFEST}"
        self.client.query(
            f"CREATE TABLE IF NOT EXISTS `{self.manifest}` (file_name STRING, table_name STRING, "
            "row_count INT64, rejected_rows INT64, loaded_at TIMESTAMP)"
        ).result()

    def loaded_files(self) -> set[str]:
        return {r.file_name for r in self.client.query(f"SELECT file_name FROM `{self.manifest}`").result()}

    def load(self, table: str, schema, rows, source_file: str) -> tuple[int, int]:
        bq = self.bq
        fq = f"{self.dataset}.{table}"
        fields = [bq.SchemaField(n, t) for n, t in schema + LINEAGE]
        self.client.create_table(
            bq.Table(fq, schema=fields), exists_ok=True
        )
        self.client.query(
            f"DELETE FROM `{fq}` WHERE source_file = @f",
            job_config=bq.QueryJobConfig(query_parameters=[bq.ScalarQueryParameter("f", "STRING", source_file)]),
        ).result()
        good = [r for r in rows if len(r) == len(schema)]
        tsv = _write_tsv(good, source_file, len(schema))
        cfg = bq.LoadJobConfig(
            schema=fields, source_format="CSV", field_delimiter="\t", quote_character="",
            max_bad_records=len(good), write_disposition="WRITE_APPEND",
        )
        try:
            with open(tsv, "rb") as fh:
                job = self.client.load_table_from_file(fh, fq, job_config=cfg)
            job.result()
        finally:
            tsv.unlink(missing_ok=True)
        n = job.output_rows or 0
        rejected = len(rows) - n
        self.client.insert_rows_json(self.manifest, [{
            "file_name": source_file, "table_name": table, "row_count": n,
            "rejected_rows": rejected, "loaded_at": datetime.now(timezone.utc).isoformat(),
        }])
        return n, rejected

    def count(self, table: str) -> int:
        return next(iter(self.client.query(f"SELECT count(*) c FROM `{self.dataset}.{table}`").result())).c


def make_backend():
    """WAREHOUSE=duckdb (default) or WAREHOUSE=bigquery."""
    target = os.getenv("WAREHOUSE", "duckdb").lower()
    if target == "bigquery":
        if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or not os.getenv("GCP_PROJECT"):
            raise SystemExit("bigquery needs GOOGLE_APPLICATION_CREDENTIALS and GCP_PROJECT")
        return BigQueryBackend(os.environ["GCP_PROJECT"], os.getenv("BQ_DATASET", "raw_gdelt"))
    return DuckDBBackend(os.getenv("DUCKDB_PATH", "data/blindspot.duckdb"))
