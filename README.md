# news-blindspot-pipeline

A small data pipeline that tracks how news stories are covered across the political spectrum and flags blindspots: stories that get heavy coverage from one side and little from the other.

It pulls public news data from [GDELT](https://www.gdeltproject.org/), groups articles into stories, joins outlet bias ratings and scores the coverage split per story. Stack: Python, DuckDB for local runs, BigQuery, dbt, Pub/Sub and Dagster.

**Status:** work in progress. Pieces get added one at a time.

## Running the ingest

```bash
pip install -e ".[dev]"
python -m blindspot.ingest.load_gdelt --hours 24
pytest
```

This pulls the last 24 hours of GDELT 2.0 Events and Mentions files (one of each every 15 minutes) into `data/blindspot.duckdb` as `raw_gdelt_events` and `raw_gdelt_mentions`. A `_load_manifest` table records every file loaded, so running it again only fetches new files.

To load into BigQuery instead, install `.[bigquery]` and set:

```bash
export WAREHOUSE=bigquery
export GCP_PROJECT=your-project
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
export BQ_DATASET=raw_gdelt   # optional
```
