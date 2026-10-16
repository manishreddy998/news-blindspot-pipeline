"""Small read and write helper so Python steps work on DuckDB and BigQuery alike."""
import os


class Warehouse:
    def __init__(self):
        self.bq = os.getenv("DBT_TARGET", "duckdb") == "bigquery"
        if self.bq:
            from google.cloud import bigquery

            self.project = os.environ["GCP_PROJECT"]
            self.client = bigquery.Client(project=self.project)
            self.mart = f"`{self.project}.analytics`"
        else:
            import duckdb

            self.con = duckdb.connect(os.getenv("DUCKDB_PATH", "data/blindspot.duckdb"))
            self.mart = "main"

    def rows(self, sql: str) -> list[dict]:
        if self.bq:
            return [dict(r.items()) for r in self.client.query(sql).result()]
        cur = self.con.execute(sql)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

    def replace_table(self, name: str, columns: list[tuple[str, str]], records: list[dict]):
        """Overwrite a table in the mart. columns are (name, BigQuery type)."""
        if self.bq:
            from google.cloud import bigquery

            schema = [bigquery.SchemaField(n, t) for n, t in columns]
            cfg = bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE", schema=schema)
            self.client.load_table_from_json(records, f"{self.project}.analytics.{name}", job_config=cfg).result()
            return
        types = {"STRING": "VARCHAR", "INT64": "BIGINT", "FLOAT64": "DOUBLE", "BOOL": "BOOLEAN",
                 "TIMESTAMP": "TIMESTAMP"}
        ddl = ", ".join(f"{n} {types[t]}" for n, t in columns)
        self.con.execute(f"create or replace table {name} ({ddl})")
        if records:
            self.con.executemany(f"insert into {name} values ({', '.join('?' * len(columns))})",
                                 [[r[n] for n, _ in columns] for r in records])
