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
from blindspot.warehouse import Warehouse

log = logging.getLogger("summaries")

TOP_SQL = """
select story_id, story_day, headline, actors, action_place, unique_articles, rated_articles,
       left_articles, center_articles, right_articles, blindspot_score, is_blindspot, blindspot_for
from {mart}.story_blindspots
where grouped_by = 'headline'
order by is_blindspot desc, unique_articles desc, story_id
limit {top}
"""
# Every headline in each story, from the clustering step.
HEADS_SQL = """
select distinct sa.story_id, sm.headline
from {mart}.story_articles sa
join {mart}.story_map sm on sm.copy_key = sa.copy_key
where sa.story_id in ({ids})
"""
URLS_SQL = "select story_id, article_url from {mart}.story_articles where story_id in ({ids})"


def run(top: int, mode: str) -> dict:
    wh = Warehouse()
    stories = wh.rows(TOP_SQL.format(mart=wh.mart, top=int(top)))
    if not stories:
        return {"stories": 0}
    ids = ", ".join(f"'{s['story_id']}'" for s in stories)
    urls: dict[str, list[str]] = {}
    for r in wh.rows(URLS_SQL.format(mart=wh.mart, ids=ids)):
        urls.setdefault(r["story_id"], []).append(r["article_url"])
    heads_by_story: dict[str, list[str]] = {}
    for r in wh.rows(HEADS_SQL.format(mart=wh.mart, ids=ids)):
        heads_by_story.setdefault(r["story_id"], []).append(r["headline"])

    now = datetime.now(timezone.utc)
    now = now.isoformat() if wh.bq else now
    records, stats = [], {"stories": len(stories), "vertex": 0, "extractive": 0, "eval_passed": 0}
    for s in stories:
        story_urls = sorted(urls.get(s["story_id"], []))
        heads = sorted(heads_by_story.get(s["story_id"], [])) or [
            h for h in (extractive.slug_to_headline(u) for u in story_urls) if h]
        method, summary = "extractive", None
        if mode == "vertex":
            from . import vertex

            try:
                summary, method = vertex.summarize(s, heads), f"vertex:{vertex.MODEL}"
            except Exception as exc:
                log.warning("vertex failed, using extractive: %s", str(exc)[:200])
        if summary is None:
            summary = extractive.summarize(s, story_urls, centroid=s.get("headline"))
        result = evaluate(summary, s, heads)
        if not result["coherent_story"]:
            log.info("low coherence %.2f for %s: %s", result["coherence"], s["story_id"][:8], summary[:80])
        stats["vertex" if method.startswith("vertex") else "extractive"] += 1
        stats["eval_passed"] += result["passed"]
        records.append({"story_id": s["story_id"], "summary": summary, "method": method,
                        "eval_passed": result["passed"], "eval_detail": json.dumps(result),
                        "created_at": now})
    wh.replace_table("story_summaries", [("story_id", "STRING"), ("summary", "STRING"), ("method", "STRING"),
                                         ("eval_passed", "BOOL"), ("eval_detail", "STRING"),
                                         ("created_at", "TIMESTAMP")], records)
    return stats


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--top", type=int, default=20)
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    print(run(args.top, os.getenv("SUMMARY_MODE", "extractive")))


if __name__ == "__main__":
    main()
