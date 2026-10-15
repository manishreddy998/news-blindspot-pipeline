"""Cheap checks on each summary. Not a quality score, a guard against bad output."""
import re

MAX_CHARS = 400
COHERENCE_MIN = 0.3


def evaluate(summary: str, story: dict, headlines: list[str]) -> dict:
    text = summary.lower()
    place_bits = [p.strip().lower() for p in (story.get("action_place") or "").split(",") if p.strip()]
    actor_bits = [a.strip().lower() for a in (story.get("actors") or "").split("/") if a.strip()]
    head_words = {w for h in headlines for w in h.lower().split() if len(w) > 4}
    # Coherence: how many of the story's headlines share 2+ content words with the
    # summary. A low number means the story grouping mixed unrelated articles.
    sw = {w for w in re.findall(r"[a-z]{4,}", text)}
    agree = [len(sw & set(re.findall(r"[a-z]{4,}", h.lower()))) >= 2 for h in set(headlines)]
    coherence = sum(agree) / len(agree) if agree else 0.0
    checks = {
        "not_empty": len(summary.strip()) > 20,
        "length_ok": len(summary) <= MAX_CHARS,
        "no_urls": not re.search(r"https?://", summary),
        # Grounded: the text names the place or an actor, or reuses headline words.
        "mentions_place_or_actor": any(b in text for b in place_bits + actor_bits),
        "uses_headline_words": not head_words or any(w in text for w in head_words),
    }
    checks["coherent_story"] = coherence >= COHERENCE_MIN
    checks["passed"] = all(checks.values())
    checks["coherence"] = round(coherence, 2)
    return checks
