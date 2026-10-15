# news-blindspot-pipeline

A small data pipeline that tracks how news stories are covered across the political spectrum and flags blindspots: stories that get heavy coverage from one side and little from the other.

It pulls public news data from [GDELT](https://www.gdeltproject.org/), groups articles into stories, joins outlet bias ratings and scores the coverage split per story. Stack: Python, DuckDB for local runs, BigQuery, dbt, Pub/Sub and Dagster.

**Status:** work in progress. Pieces get added one at a time.
