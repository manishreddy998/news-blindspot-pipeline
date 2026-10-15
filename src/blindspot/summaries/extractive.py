"""Summaries built only from what we already have: article URLs and story counts.

Most news URLs end in a slug that is the headline in lowercase, for example
.../2026-10-15-judge-limits-doj-access-in-ilhan-omar-investigation/. We turn
slugs back into headlines and pick the one that shares the most words with
the other headlines in the story, so a single odd article can't become the label.
"""
import re
from collections import Counter

# Numbers, hex IDs (uuid chunks like 8d11) and file endings are not headline words.
_ID_BITS = re.compile(r"^[0-9a-f]*\d[0-9a-f]*$|^[0-9a-f]{8,}$|^(html?|php|aspx?|amp|article|story|news)$")
_STOP = {"the", "a", "an", "of", "to", "in", "on", "for", "and", "or", "at", "by", "with", "is", "are",
         "as", "from", "after", "over", "new", "says", "say", "its", "be", "has", "was", "will"}


def slug_to_headline(url: str) -> str | None:
    path = re.sub(r"[?#].*", "", url).rstrip("/")
    slug = path.rsplit("/", 1)[-1]
    slug = re.sub(r"\.(s?html?|php|aspx?)$", "", slug)
    words = [w for w in re.split(r"[-_.+]+", slug.lower()) if w and not _ID_BITS.match(w)]
    if len(words) < 4:
        return None
    text = " ".join(words)
    return text[0].upper() + text[1:]


def _content_words(text: str) -> set[str]:
    return {w for w in text.lower().split() if w not in _STOP and len(w) > 2}


def pick_headline(urls: list[str]) -> str | None:
    heads = [h for h in (slug_to_headline(u) for u in urls) if h]
    if not heads:
        return None
    counts = Counter(w for h in set(heads) for w in _content_words(h))

    def score(h):
        words = _content_words(h)
        return (sum(counts[w] - 1 for w in words) / max(len(words), 1), -len(h))

    return max(set(heads), key=score)


def summarize(story: dict, urls: list[str]) -> str:
    head = pick_headline(urls) or f"{story['actors'] or 'Unnamed actors'} in {story['action_place'] or 'an unknown place'}"
    split = f"left {story['left_articles']}, center {story['center_articles']}, right {story['right_articles']}"
    text = (f"{head}. {story['unique_articles']} unique articles; rated outlets: {split}. "
            f"Place: {story['action_place'] or 'unknown'}.")
    return text[:400]
