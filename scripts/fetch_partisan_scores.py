"""Download the partisan audience scores from Robertson et al. (2018) and write the dbt seed.

Source: Robertson, R. E., Jiang, S., Joseph, K., Friedland, L., Lazer, D., & Wilson, C. (2018).
Auditing Partisan Audience Bias within Google Search. Proc. ACM Hum.-Comput. Interact. 2(CSCW), 148.
https://doi.org/10.1145/3274417
Data: "Partisan Bias Scores for Web Domains", Harvard Dataverse, https://doi.org/10.7910/DVN/QAN5VX
License: CC0 1.0. The authors ask that you cite the paper.

Only the authors' own `score` column is kept. The file also carries scores from other
projects (AllSides, Pew, Budak et al.) that come with their own terms, so we leave those out.

    python scripts/fetch_partisan_scores.py
"""
import csv
import io
from pathlib import Path

import requests

URL = "https://dataverse.harvard.edu/api/access/datafile/3316961"
OUT = Path(__file__).resolve().parents[1] / "dbt" / "seeds" / "partisan_audience_scores.csv"


def main():
    text = requests.get(URL, timeout=60).text
    rows = []
    for r in csv.DictReader(io.StringIO(text), delimiter="\t"):
        domain = r["domain"].strip().strip('"').lower()
        if domain and r["score"].strip():
            rows.append((domain, float(r["score"])))
    rows.sort()
    with OUT.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["domain", "partisan_score"])
        w.writerows(rows)
    print(f"wrote {len(rows)} domains to {OUT}")


if __name__ == "__main__":
    main()
