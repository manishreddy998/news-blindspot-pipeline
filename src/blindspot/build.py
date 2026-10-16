"""Build everything after the load, in the right order:

1. dbt staging models (clean events, mentions and article copies)
2. headline clustering, which writes story_map
3. the rest of dbt (stories, blindspots, tests)

    python -m blindspot.build
"""
import os
import subprocess
import sys
from pathlib import Path

DBT_DIR = Path(os.getenv("DBT_PROJECT_DIR", Path(__file__).resolve().parents[2] / "dbt"))


def dbt(*args: str) -> None:
    subprocess.run(["dbt", *args, "--profiles-dir", "."], cwd=DBT_DIR, check=True)


def main() -> int:
    from blindspot.stories.cluster import run as cluster

    try:
        dbt("seed")
        dbt("build", "--select", "staging")
        print(cluster())
        dbt("build", "--exclude", "staging")
    except subprocess.CalledProcessError as exc:
        print(f"dbt failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
