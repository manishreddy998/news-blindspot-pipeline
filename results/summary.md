# Results snapshot: October 16, 2026

One fresh run from an empty database, done in Docker. The bias ratings are **example data**, so the blindspot flags show how the method works, not real media bias.

## Window
- 24 hours of GDELT 2.0, pinned with `--end 20261016150000`.
- Files stamped **Oct 15, 11:15 AM ET** through **Oct 16, 11:00 AM ET** (15:15 to 15:00 UTC).
- 192 files (96 events, 96 mentions). None missing, no rows rejected. The load took about 75 seconds.

## Volume
| What | Count |
|---|---|
| Raw events | 118,290 |
| Raw mentions | 310,068 |
| Web article mentions after cleanup | 304,348 |
| Distinct outlets | 4,895 |
| Mentions that join to a loaded event | 81.0% |

## Stories
- **35,927 stories**, and 2,618 of them have 5 or more articles.
- The biggest has 739 articles from 442 outlets (placed in Tennessee, United States).

## Syndicated copies
- 50,393 article URLs collapse to **32,914 unique articles**.
- 17,462 URLs (34.7%) are copies of an article posted on 3 or more sites.
- The biggest copy group is one celebrity story on **642 sites**, all iheart.com local radio pages. Of 3,164 iheart.com URLs, 3,135 are copies.

## Blindspots (example bias data)
- 3,399 story articles come from outlets in the example lean list.
- 43 stories have at least 5 rated articles, so they can be scored.
- **9 are flagged:** 5 are a blindspot for the left (mostly right coverage) and 4 for the right.

Top flagged stories (left / center / right counts from rated outlets):

| Story (headline from URLs) | Place | L / C / R | Blindspot for |
|---|---|---|---|
| US seeks to break Canada, Carney says as Alberta votes | Cape Breton, Nova Scotia | 1 / 11 / 0 | right |
| Prince Harry and Meghan Markle | United Kingdom | 1 / 0 / 7 | left |
| Martin Lewis says I would | unknown | 7 / 0 / 1 | right |
| Hillary Clinton admits near fainting episode was a mistake | Cornell University, New York | 1 / 1 / 4 | left |
| Shooter killed at US school | Oregon | 0 / 0 / 5 | left |
| Katie Zacharia press secretary interview | Washington, DC | 4 / 0 / 1 | right |

Two things these rows show:
- The Canada story is flagged on 1 left article against 0 right, while 11 center articles carry most of its coverage. The rule should also need a minimum number of left plus right articles.
- The labels come from URL slugs, so some are rough ("Martin Lewis says I would").

## Quality checks
- **dbt build:** 20 of 20 passed (models, seed and tests).
- **Source freshness:** passed for events and mentions.
- **Python quality check** (exit code 0):

```
ok   raw events loaded: 118290
ok   stories built: 35927
ok   mentions joined to events: 0.810
ok   stories with a scored split: 2210
ok   scores out of range: 0
ok   syndicated share of articles: 0.347
```

## Summaries
- 20 top stories summarized with the extractive method. Gemini on Vertex AI is not enabled in the project yet.
- **Eval: 2 of 20 passed**, average coherence 0.14.
- Most fail the coherence check: the story's headlines don't share much wording. That points at the story grouping, which is too coarse, rather than at the summary step.

## Screenshots
See `docs/images/`: dashboard top, blindspot list, lean split, and the Dagster assets, runs and schedule pages.
