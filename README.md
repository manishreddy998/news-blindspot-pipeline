# news-blindspot-pipeline

## Intro
When a big story breaks, outlets on the left and right often cover it very differently, and sometimes one side barely covers it at all. Those gaps are called blindspots. This project is a small, working pipeline that finds them in public news data, end to end: pull the data, group articles into stories, count coverage by outlet lean, and show the results on a dashboard.

It's a prototype I built to understand the problem properly, so it is honest about what works and what doesn't yet.

## Objective
For every news story in the last day, answer three questions:
1. Who covered it, and how many unique articles were there?
2. How did the coverage split between left, center and right outlets?
3. Is one side mostly ignoring it?

And keep the answers fresh every 15 minutes, with tests that stop bad numbers before anyone sees them.

## Data source
[GDELT 2.0](https://www.gdeltproject.org/) watches news sites around the world and publishes two files every 15 minutes:
- **Events**: who did what to whom, where, coded with CAMEO event codes.
- **Mentions**: every article that mentioned an event, with the outlet and the URL.

It's free and public, and a day is roughly 120k events and 300k mentions from almost 5,000 outlets.

## How we pull the data
`python -m blindspot.ingest.load_gdelt --hours 24`
- It works out the 15 minute file names for the window from GDELT's `lastupdate.txt`, so it never downloads the huge master file list.
- Every loaded file is recorded in a `_load_manifest` table. Running it again only fetches new files.
- For each file it deletes that file's rows and then inserts them, so a file that half loaded before is replaced, not doubled.
- `--end` pins the window, which lets you compare two runs row for row.
- The same code writes to DuckDB on your laptop or to BigQuery (`WAREHOUSE=bigquery`). The BigQuery raw tables are clustered on the source file, so these per file deletes stay cheap.

## Transformations with dbt
The `dbt/` project runs unchanged on DuckDB and BigQuery.
- **Staging**: GDELT dates like `20261015193000` become real timestamps, duplicates are removed, and only web articles are kept. On BigQuery, staging tables are split into daily partitions, so a query over the last few days only reads those days.
- **Article copies**: syndication networks post one article on hundreds of sites. Copies share the same URL slug, so a slug seen on 3 or more sites is treated as one article.
- **Stories**: events that share the same actors, the same kind of action, the same country and the same day form one story. Simple and explainable, though coarse (see limits).
- **Outlet lean**: a small seed file (`dbt/seeds/outlet_bias.csv`) maps outlet domains to left, center or right. **It is example data**, not a real rating.
- **Blindspots**: for each story we count unique articles by lean. Left share is left over (left plus right). A story is flagged when it has at least 5 rated articles and one side has 80% or more of the left plus right coverage. In the table, the score is |2 x left share minus 1|, so an 80% split shows as 0.60 and 100% shows as 1.00.

## Data quality
Checks run on every build:
- Freshness on the raw tables: warn after 2 hours with no new data, error after 6.
- Row counts that must match between raw and staging.
- Share of mentions that join to a loaded event (warns below 80%).
- Scores and shares between 0 and 1, lean counts that add up, and every flag says which side is missing.
- `python -m blindspot.quality.check` looks over the final tables and exits with code 1 if anything is off, so the scheduled run stops there.

## Summaries
`python -m blindspot.summaries.run --top 20` writes a one line summary for the top stories.
- By default it rebuilds headlines from article URLs and picks the one most like the others. No key needed, and it can't make anything up.
- `SUMMARY_MODE=vertex` asks Gemini on Vertex AI for one neutral sentence from the headlines. If the call fails, it falls back to the URL headlines.
- Every summary is checked for length, URLs, mention of the place or actors, and **coherence**: how many of the story's headlines share wording with it. A low coherence score usually means the story mixes unrelated articles.

## Orchestration with Dagster
Four assets run in order every 15 minutes: `gdelt_raw`, then `dbt_models` (build plus tests), then `quality_check`, then `story_summaries`. If a step fails, the steps after it don't run, so a bad load never reaches the dashboard. Each run loads the last hour of files and skips what's already there, which makes missed runs catch up on their own.

## Dashboard
A small Streamlit app with:
- a banner saying the bias data is example data
- story and blindspot counts
- the flagged stories with their split
- a left / center / right bar chart for the top stories
- a table you can filter

It opens the database read only, so it never blocks the pipeline.

## Results
From a fresh 24 hour run (Oct 15, 11:15 AM ET to Oct 16, 11:00 AM ET). Full numbers are in [results/summary.md](results/summary.md).
- 192 files, 118,290 events, 310,068 mentions, 4,895 outlets
- 35,927 stories
- 50,393 article URLs collapse to 32,914 unique articles. One story was posted on 642 sites.
- 43 stories could be scored and 9 were flagged, with example bias data
- dbt 20 of 20 passed, freshness passed, quality check passed
- Summary eval: 2 of 20 coherent

![Dashboard](docs/images/dashboard-top.png)
![Blindspot list](docs/images/dashboard-blindspots.png)
![Lean split](docs/images/dashboard-lean-split.png)
![Dagster runs](docs/images/dagster-runs.png)
![Dagster assets](docs/images/dagster-assets.png)
![Dagster schedule](docs/images/dagster-schedule.png)

## Honest limits
- **The bias data is example data.** The leans in the seed are placeholders I picked, not ratings from any service. The flags show the method works. They say nothing real about any outlet. A licensed source (AllSides, Ad Fontes Media or similar) would replace it.
- **Story grouping is coarse.** Grouping by actors, action, country and day puts unrelated news together, which is why only 2 of 20 summaries pass the coherence check.
- **Few rated articles.** GDELT is very global and the seed is small, so only about 1% of articles have a lean.
- **The flag rule is too easy to trigger.** A story can be flagged on 1 left article against 0 right when most coverage is center. It should also need a minimum number of left plus right articles.
- **Copy detection is simple.** It misses copies that get a new headline.
- **DuckDB has one writer.** Fine for a laptop. In production the dashboard would read from BigQuery.

## How to run with Docker
You only need Docker Desktop.

```bash
git pull
docker compose up --build dagster dashboard
```

- Dagster: http://localhost:3000
- Dashboard: http://localhost:8501
- Stop with Ctrl+C, then `docker compose down`.
- Add `SCHEDULE_ON=0` in front to keep the 15 minute schedule off.

On a first run, the database is empty. You can load and build by hand:

```bash
docker compose run --rm pipeline python -m blindspot.ingest.load_gdelt --hours 24
docker compose run --rm -w /app/dbt pipeline dbt build --profiles-dir .
docker compose run --rm pipeline python -m blindspot.quality.check
docker compose run --rm pipeline python -m blindspot.summaries.run --top 20
docker compose run --rm pipeline pytest
```

Compose rebuilds the image whenever you run it, so pulled changes to dependencies are always picked up. If anything looks stale, run `docker compose build --no-cache`.

**BigQuery.** Keep the service account key outside the repo and point `GCP_KEY_PATH` at it. It's mounted read only and never copied into the image.

```bash
export GCP_KEY_PATH=$HOME/.secrets/gcp-groundnews.json
WAREHOUSE=bigquery GCP_PROJECT=your-project \
  docker compose run --rm pipeline python -m blindspot.ingest.load_gdelt --hours 24
DBT_TARGET=bigquery GCP_PROJECT=your-project \
  docker compose run --rm -w /app/dbt pipeline dbt build --profiles-dir .
```

## Next steps
1. Group stories by headline text (or embeddings) within a time window, then rerun the coherence check to see the gain.
2. Swap the example seed for a licensed bias rating source.
3. Add a minimum left plus right article count to the blindspot rule.
4. Use canonical URLs from article pages for better copy detection.
5. Turn on Gemini summaries once the Vertex AI API is enabled, and keep the same checks.
6. Run the schedule in the cloud (Cloud Run jobs and Cloud Scheduler) with the dashboard reading from BigQuery.
