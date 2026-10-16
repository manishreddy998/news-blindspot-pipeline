from blindspot.summaries import extractive
from blindspot.summaries.evaluate import evaluate

STORY = {"actors": "UNITED STATES", "action_place": "Minneapolis, Minnesota, United States",
         "unique_articles": 3, "left_articles": 1, "center_articles": 0, "right_articles": 2}
URLS = [
    "https://wtag.iheart.com/content/2026-10-15-judge-limits-doj-access-in-ilhan-omar-investigation/",
    "https://example.com/news/judge-limits-doj-access-to-omar-records-12345678",
    "https://other.com/politics/2026/10/15/minnesota-judge-limits-doj-in-omar-probe.html",
]


def test_slug_to_headline_drops_dates_and_ids():
    assert extractive.slug_to_headline(URLS[0]) == "Judge limits doj access in ilhan omar investigation"
    assert extractive.slug_to_headline("https://x.com/a/123") is None


def test_pick_headline_prefers_the_shared_wording():
    assert "judge limits doj" in extractive.pick_headline(URLS).lower()


def test_extractive_summary_passes_eval():
    heads = [extractive.slug_to_headline(u) for u in URLS]
    summary = extractive.summarize(STORY, URLS)
    assert evaluate(summary, STORY, heads)["passed"]


def test_eval_catches_bad_output():
    heads = [extractive.slug_to_headline(u) for u in URLS]
    bad = evaluate("Click here https://spam.example " + "x" * 500, STORY, heads)
    assert not bad["passed"] and not bad["length_ok"] and not bad["no_urls"]


def test_uuid_slugs_are_not_headlines():
    assert extractive.slug_to_headline("https://x.com/article/baf6c1d2-482a-4c3e-8d11-0a1b2c3d4e5f") is None


def test_centroid_headline_leads_the_summary():
    summary = extractive.summarize(STORY, URLS, centroid="judge limits doj access in omar case us")
    assert summary.startswith("Judge limits DOJ access in omar case US.")
