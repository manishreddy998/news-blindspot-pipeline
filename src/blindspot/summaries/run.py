"""Summarize the top stories and save them to story_summaries.

    python -m blindspot.summaries.run --top 20
    SUMMARY_MODE=vertex python -m blindspot.summaries.run   # Gemini, needs Vertex AI enabled
"""
import argparse
import json
import logging
import os
from datetime import datetime, timezone

from . import extractive
from .evaluate import evaluate

log = logging.getLogger("summaries")

TOP_SQL = """
select story_id, story_day, actors, action_place, unique_articles, rated_articles,
       left_articles, center_articles, right_articles, blindspot_score, is_blindspot, blindspot_for
from {mart}.story_blindspots
where grouped_by = 'headline'
order by is_blindspot desc, unique_articles desc
limit {top}
"""
URLS_SQL = "select story_id, article_url from {mart}.story_articles where story_id in ({ids})"


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

    def save(self, records: list[dict]):
        if self.bq:
            from google.cloud import bigquery

            cfg = bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE", autodetect=True)
            self.client.load_table_from_json(records, f"{self.project}.analytics.story_summaries",
                                             job_config=cfg).result()
            return
        self.con.execute("create or replace table story_summaries (story_id varchar, summary varchar, "
                         "method varchar, eval_passed boolean, eval_detail varchar, created_at timestamp)")
        self.con.executemany("insert into story_summaries values (?, ?, ?, ?, ?, ?)",
                             [[r[k] for k in ("story_id", "summary", "method", "eval_passed",
                                              "eval_detail", "created_at")] for r in records])


def run(top: int, mode: str) -> dict:
    wh = Warehouse()
    stories = wh.rows(TOP_SQL.format(mart=wh.mart, top=int(top)))
    if not stories:
        return {"stories": 0}
    ids = ", ".join(f"'{s['story_id']}'" for s in stories)
    urls: dict[str, list[str]] = {}
    for r in wh.rows(URLS_SQL.format(mart=wh.mart, ids=ids)):
        urls.setdefault(r["story_id"], []).append(r["article_url"])

    now = datetime.now(timezone.utc).isoformat()
    records, stats = [], {"stories": len(stories), "vertex": 0, "extractive": 0, "eval_passed": 0}
    for s in stories:
        story_urls = sorted(urls.get(s["story_id"], []))
        heads = [h for h in (extractive.slug_to_headline(u) for u in story_urls) if h]
        method, summary = "extractive", None
        if mode == "vertex":
            from . import vertex

            try:
                summary, method = vertex.summarize(s, heads), f"vertex:{vertex.MODEL}"
            except Exception as exc:
                log.warning("vertex failed, using extractive: %s", str(exc)[:200])
        if summary is None:
            summary = extractive.summarize(s, story_urls)
        result = evaluate(summary, s, heads)
        if not result["coherent_story"]:
            log.info("low coherence %.2f for %s: %s", result["coherence"], s["story_id"][:8], summary[:80])
        stats["vertex" if method.startswith("vertex") else "extractive"] += 1
        stats["eval_passed"] += result["passed"]
        records.append({"story_id": s["story_id"], "summary": summary, "method": method,
                        "eval_passed": result["passed"], "eval_detail": json.dumps(result),
                        "created_at": now})
    wh.save(records)
    return stats


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--top", type=int, default=20)
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    print(run(args.top, os.getenv("SUMMARY_MODE", "extractive")))


if __name__ == "__main__":
    main()
