"""Group articles into stories by headline similarity.

GDELT links articles to coded events, but one article creates many events and
the actor and place fields are often too vague to tell stories apart ("UNITED
STATES" doing something somewhere). Headlines say what a story is about, and
most news URLs end in the headline. So:

1. Take one headline per unique article (copies of a syndicated article share
   one copy_key from stg_article_copies, so they count once).
2. Turn headlines into TF-IDF vectors (words and word pairs, English stop
   words removed).
3. Link two headlines when their cosine similarity is at least SIM_MIN and
   they were first seen within WINDOW_HOURS of each other.
4. Each connected group of links is a story.

The result goes to story_map (copy_key -> story_id). Articles whose URL has no
usable headline keep the event based story from dbt.

    python -m blindspot.stories.cluster
"""
import argparse
import hashlib
import logging
import os

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors

from blindspot.summaries.extractive import slug_to_headline
from blindspot.warehouse import Warehouse

log = logging.getLogger("cluster")

# Tuned on the Oct 15 to 16 window: 0.3 and 0.4 chain unrelated stories into one
# giant group, 0.6 splits real stories apart. See results/summary.md.
SIM_MIN = float(os.getenv("CLUSTER_SIM_MIN", "0.5"))
WINDOW_HOURS = float(os.getenv("CLUSTER_WINDOW_HOURS", "36"))

ARTICLES_SQL = """
select c.copy_key, min(c.article_url) as sample_url, min(m.mentioned_at) as first_seen_at
from {mart}.stg_article_copies c
join {mart}.stg_gdelt_mentions m on m.article_url = c.article_url
group by 1
"""

COLUMNS = [("copy_key", "STRING"), ("story_id", "STRING"), ("headline", "STRING"),
           ("story_headline", "STRING"), ("first_seen_at", "TIMESTAMP")]


def cluster(headlines: list[str], seen_hours: np.ndarray, sim_min: float = SIM_MIN,
            window_hours: float = WINDOW_HOURS) -> tuple[np.ndarray, list[int]]:
    """Return a story label per headline and, per label, the index of its most central headline."""
    n = len(headlines)
    if n == 0:
        return np.array([], dtype=int), []
    vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=2 if n > 50 else 1,
                          sublinear_tf=True)
    X = vec.fit_transform(headlines)
    nn = NearestNeighbors(radius=1 - sim_min, metric="cosine", algorithm="brute").fit(X)
    graph = nn.radius_neighbors_graph(X, mode="connectivity").tocoo()
    keep = np.abs(seen_hours[graph.row] - seen_hours[graph.col]) <= window_hours
    graph = csr_matrix((np.ones(keep.sum()), (graph.row[keep], graph.col[keep])), shape=(n, n))
    _, labels = connected_components(graph, directed=False)

    # The representative headline is the one closest to the story's average vector.
    centres = []
    order = np.argsort(labels, kind="stable")
    bounds = np.flatnonzero(np.diff(labels[order])) + 1
    for idx in np.split(order, bounds):
        centroid = np.asarray(X[idx].mean(axis=0)).ravel()
        centres.append(int(idx[np.argmax(X[idx] @ centroid)]))
    return labels, centres


def run() -> dict:
    wh = Warehouse()
    rows = wh.rows(ARTICLES_SQL.format(mart=wh.mart))
    items = [(r, h) for r in rows if (h := slug_to_headline(r["sample_url"]))]
    if not items:
        wh.replace_table("story_map", COLUMNS, [])
        return {"articles": len(rows), "with_headline": 0, "stories": 0}
    t0 = min(r["first_seen_at"] for r, _ in items)
    hours = np.array([(r["first_seen_at"] - t0).total_seconds() / 3600 for r, _ in items])
    labels, centres = cluster([h for _, h in items], hours)
    centre_of = {int(labels[i]): i for i in centres}

    records = []
    for i, (r, head) in enumerate(items):
        c = centre_of[int(labels[i])]
        anchor = items[c][0]["copy_key"]
        records.append({
            "copy_key": r["copy_key"],
            "story_id": hashlib.md5(f"headline|{anchor}".encode()).hexdigest(),
            "headline": head,
            "story_headline": items[c][1],
            "first_seen_at": r["first_seen_at"].isoformat() if wh.bq else r["first_seen_at"],
        })
    wh.replace_table("story_map", COLUMNS, records)
    sizes = np.bincount(labels)
    return {"articles": len(rows), "with_headline": len(items), "stories": int(len(sizes)),
            "multi_article_stories": int((sizes > 1).sum()), "largest": int(sizes.max())}


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    print(run())


if __name__ == "__main__":
    main()
