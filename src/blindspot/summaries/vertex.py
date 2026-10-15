"""Optional Gemini summary through Vertex AI. Only used with SUMMARY_MODE=vertex.

Needs the Vertex AI API enabled in the project and the service account to have
the Vertex AI User role. If the call fails we raise, and the caller falls back
to the extractive summary and records why.
"""
import os

import requests

MODEL = os.getenv("VERTEX_MODEL", "gemini-2.5-flash")
LOCATION = os.getenv("VERTEX_LOCATION", "us-central1")

PROMPT = """Write one neutral sentence (max 40 words) saying what this news story is about.
Use only the headlines below. Do not guess facts that are not in them. No opinions.

Place: {place}
Actors: {actors}
Headlines:
{heads}"""


def _token() -> str:
    import google.auth
    import google.auth.transport.requests

    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(google.auth.transport.requests.Request())
    return creds.token


def summarize(story: dict, headlines: list[str], session=None) -> str:
    project = os.environ["GCP_PROJECT"]
    url = (f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{project}/locations/{LOCATION}"
           f"/publishers/google/models/{MODEL}:generateContent")
    body = {
        "contents": [{"role": "user", "parts": [{"text": PROMPT.format(
            place=story["action_place"], actors=story["actors"],
            heads="\n".join(f"- {h}" for h in headlines[:15]))}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 120},
    }
    s = session or requests
    resp = s.post(url, json=body, headers={"Authorization": f"Bearer {_token()}"}, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"vertex {resp.status_code}: {resp.text[:300]}")
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
