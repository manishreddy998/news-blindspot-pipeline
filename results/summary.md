# Results snapshot: October 16, 2026 (after the analysis fixes)

A fresh run from an empty database in Docker, on the same pinned window as the first snapshot. Before and after numbers use the same raw data.

## Window
- 24 hours of GDELT 2.0, `--end 20261016150000`.
- Files stamped **Oct 15, 11:15 AM ET** through **Oct 16, 11:00 AM ET**.
- 192 files. None missing, no rows rejected.

## Volume
| What | Count |
|---|---|
| Raw events | 118,290 |
| Raw mentions | 310,068 |
| Web article mentions after cleanup | 304,348 |
| Distinct outlets | 4,895 |
| Mentions that join to a loaded event | 81.0% |

## Syndicated copies
- 50,393 article URLs collapse to **32,914 unique articles**.
- 17,462 URLs (34.7%) are copies posted on 3 or more sites.
- The biggest copy group is one celebrity story on 642 iheart.com local radio pages.

## Stories
Headline clustering uses TF-IDF on URL headlines, links at cosine similarity 0.5 or more within 36 hours, and takes connected groups.

| | Before (actor, action, country, day) | After (headline clusters) |
|---|---|---|
| Stories | 35,927 | 23,175 |
| Unique articles grouped by headline | 0 | 23,872 directly, plus 5,656 via shared events |
| Articles left on event grouping | all | 2,708 (8%) |
| Biggest story | 739 articles, mixed topics in "Tennessee" | Oregon elementary school shooting, 491 unique articles from 752 outlets |

Tuning the similarity threshold on this window:

| Threshold | Stories | Biggest group | Top 20 average coherence |
|---|---|---|---|
| 0.3 | 6,301 | 13,715 (chained) | 0.65 |
| 0.4 | 14,055 | 1,268 (chained) | 0.60 |
| **0.5** | **18,066** | **268** | **0.91** |
| 0.6 | 20,047 | 156 | 0.97 (but real stories split) |

## Outlet lean
- Source: Robertson et al. (2018), "Auditing Partisan Audience Bias within Google Search", Harvard Dataverse doi:10.7910/DVN/QAN5VX, **CC0 1.0**.
- 19,022 domains in the file. Bucketed as left (score -0.2 or less) 6,595, center 7,277, right 5,150.
- 1,483 of the 4,895 GDELT outlets match, covering **42.1% of mentions**. The old example list covered about 1%.
- Unique story articles by lean: left 4,546, center 7,731, right 3,797.

## Blindspots
The rule now needs a headline story with **at least 4 left plus right articles**, and **80% or more** on one side. Each flag carries a 95% Wilson interval on that share. It's "strong" when the low end is still above 50%.

| | Before | After |
|---|---|---|
| Lean data | example list | Robertson et al. 2018, CC0 |
| Stories that can be judged | 43 | 137 |
| Flagged | 9 | **71** |
| Blindspot for the left / right | 5 / 4 | 47 / 24 |
| Strong / weak | not measured | 49 / 22 |

Top flagged stories, by the low end of the interval (left / center / right):

| Story | L / C / R | 95% low end | Blindspot for |
|---|---|---|---|
| IShowSpeed backs, eyes Ghana cinema release | 0 / 8 / 11 | 74% | left |
| Massachusetts AG joins effort to protect AI chatbot data | 0 / 11 / 11 | 74% | left |
| Al Pacino to receive SAG-AFTRA lifetime achievement award | 1 / 16 / 13 | 69% | left |
| Sally Rooney book sales paused in UK over Palestine Action support | 8 / 1 / 0 | 68% | right |
| Wahpeton man charged with felonies in child abuse case | 1 / 11 / 12 | 67% | left |
| Vatican games out possible Sunday prayer appearance as Pope Leo recovers from lung surgery | 1 / 12 / 11 | 65% | left |
| Carroll restaurant wins Iowa breaded pork tenderloin contest | 0 / 0 / 7 | 65% | left |
| Iranian negotiator insists US keep the deal | 0 / 7 / 7 | 65% | left |

Top blindspots for the right:

| Story | L / C / R | 95% low end |
|---|---|---|
| Sally Rooney book sales paused in UK over Palestine Action support | 8 / 1 / 0 | 68% |
| Brighton SEND reform plan approved | 6 / 5 / 0 | 61% |
| New report: NSP fails benchmarks | 6 / 0 / 0 | 61% |
| FG reopens first Niger bridge after closure | 5 / 0 / 0 | 57% |
| CJP Lehra Do Tiranga march: Abhijeet Dipke detained by Delhi police | 7 / 15 / 1 | 53% |

The biggest stories are not flagged, and their splits look balanced:
- Oregon school shooting: 62 / 163 / 99
- Katie Zacharia press secretary story: 69 / 91 / 43
- Fort Hood execution livestream: 40 / 73 / 49

What the flags show:
- Many flags for the left are local or soft news. Local radio and TV sites often have right leaning audiences in this data.
- Most flags for the right are UK, Indian and Nigerian stories carried by outlets with left leaning US audiences.

## Quality checks
- **dbt build:** 20 of 20 passed (seed, models and tests, including the new rule test).
- **Source freshness:** passed for events and mentions.
- **Reruns:** two rebuilds on the same data give the same 71 flags.
- **Python quality check** (exit code 0):

```
ok   raw events loaded: 118290
ok   stories built: 23175
ok   mentions joined to events: 0.810
ok   stories with a scored split: 7078
ok   scores out of range: 0
ok   syndicated share of articles: 0.347
```

## Summary eval
The Vertex AI API is still disabled in the project (403 on Oct 16), so every summary is extractive. It leads with the story's most central headline.

| | Passed | Average coherence |
|---|---|---|
| Before (event stories, URL headline pick), top 20 | 2 of 20 | 0.14 |
| Headline clusters, old summary method, top 20 | 18 of 20 | 0.89 |
| **Headline clusters, centroid headline, top 20** | **19 of 20** | **0.99** |
| Same, top 100 | 89 of 100 | 0.95 |

The one top 20 miss is "Brighton SEND reform plan approved". Its coherence is 1.0, but GDELT gives it no place or actor, so the "mentions place or actor" check fails. The top 20 list breaks ties on story id, so DuckDB and BigQuery pick the same stories and write identical summaries.

## BigQuery
The same window was run on BigQuery (project groundnews-prototype). The raw rows were copied into a `raw_gdelt_snapshot` dataset so that older loads in `raw_gdelt` don't mix in, and the build ran with `BQ_DATASET=raw_gdelt_snapshot`.
- Raw: 118,290 events, 310,068 mentions, 192 files, matching DuckDB.
- Headline clustering: the same 23,872 headlines and 18,063 stories, 23,175 stories in all.
- dbt 20 of 20 passed, and the quality check gave the same six values.
- **The same 71 flagged story ids** (47 for the left, 49 strong).
- Identical top 20 summaries, 19 of 20 passing.

## Screenshots
See `docs/images/`: dashboard top, blindspot list, lean split, and the Dagster assets, runs and schedule pages.
