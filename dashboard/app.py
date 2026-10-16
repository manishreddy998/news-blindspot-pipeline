"""Blindspot dashboard: top stories, their lean split and blindspot flags.

    streamlit run dashboard/app.py
"""
import os

import duckdb
import pandas as pd
import streamlit as st

DB = os.getenv("DUCKDB_PATH", "data/blindspot.duckdb")

st.set_page_config(page_title="News blindspots", layout="wide")


@st.cache_data(ttl=60)
def load():
    # Read only, so the pipeline can keep writing. If a write holds the lock, show the last copy.
    con = duckdb.connect(DB, read_only=True)
    try:
        stories = con.execute("""
            select b.*, s.summary, s.eval_passed
            from story_blindspots b
            left join story_summaries s using (story_id)
            order by b.unique_articles desc
        """).df()
        meta = con.execute("""
            select (select max(file_name) from _load_manifest) as last_file,
                   (select count(*) from stories) as stories,
                   (select count(*) from story_blindspots where is_blindspot) as blindspots
        """).df().iloc[0]
    finally:
        con.close()
    return stories, meta


st.info("**Outlet lean** comes from partisan audience scores by Robertson et al. (2018), released "
        "under CC0 on Harvard Dataverse. A score says who shares an outlet on Twitter, not how it writes, "
        "and the data dates from 2017.")
st.title("News blindspots")

try:
    stories, meta = load()
except duckdb.IOException:
    st.info("The pipeline is writing right now. Refresh in a few seconds.")
    st.stop()

c1, c2, c3 = st.columns(3)
c1.metric("Stories", f"{meta.stories:,}")
c2.metric("Blindspots flagged", int(meta.blindspots))
c3.metric("Latest GDELT file", str(meta.last_file)[:12])

min_rated = st.sidebar.slider("Min articles from rated outlets", 0, 30, 4)
only_flags = st.sidebar.checkbox("Only blindspots", value=False)
view = stories[stories.rated_articles >= min_rated]
if only_flags:
    view = view[view.is_blindspot]

st.subheader("Blindspots")
flags = stories[stories.is_blindspot].sort_values(["dominant_share_low", "sided_articles"], ascending=False).head(10)
for _, r in flags.iterrows():
    side = "the left" if r.blindspot_for == "left" else "the right"
    label = r.summary if isinstance(r.summary, str) else f"{r.actors or 'Unnamed'} in {r.action_place or 'unknown place'}"
    st.markdown(f"**{label}**  \n"
                f"Blindspot for {side}: left {r.left_articles}, center {r.center_articles}, right {r.right_articles}"
                f" · {r.dominant_share:.0%} one side (95% low end {r.dominant_share_low:.0%}, {r.confidence})")

st.subheader("Coverage split for top stories")
top = view.head(15).copy()
fallback = top.actors.fillna("").replace("", "Unnamed") + " / " + top.action_place.fillna("unknown place")
top["label"] = top.summary.fillna(fallback).str.split(".").str[0].str.slice(0, 60)
split = top.set_index("label")[["left_articles", "center_articles", "right_articles"]]
split.columns = ["left", "center", "right"]
st.bar_chart(split, horizontal=True, color=["#3b6fd8", "#9a9a9a", "#d8433b"])

st.subheader("All scored stories")
cols = ["story_day", "headline", "actors", "action_place", "unique_articles", "rated_articles", "left_articles",
        "center_articles", "right_articles", "blindspot_score", "dominant_share_low", "is_blindspot", "confidence", "blindspot_for", "summary"]
st.dataframe(pd.DataFrame(view[cols]), use_container_width=True, hide_index=True)
