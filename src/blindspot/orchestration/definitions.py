"""Dagster wiring: load GDELT, build dbt, check quality, summarize. Every 15 minutes.

    dagster dev -m blindspot.orchestration.definitions
"""
import os
import subprocess
import sys
from pathlib import Path

from dagster import (AssetExecutionContext, DefaultScheduleStatus, Definitions, MaterializeResult,
                     MetadataValue, ScheduleDefinition, asset, define_asset_job)

DBT_DIR = Path(os.getenv("DBT_PROJECT_DIR", Path(__file__).resolve().parents[3] / "dbt"))


def _run(context: AssetExecutionContext, cmd: list[str], cwd: Path | None = None) -> str:
    context.log.info("running: %s", " ".join(cmd))
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    out = (proc.stdout + proc.stderr)[-4000:]
    if proc.returncode != 0:
        raise RuntimeError(f"{cmd[0]} failed with code {proc.returncode}\n{out}")
    return out


@asset(group_name="ingest", description="Latest GDELT events and mentions. Reruns skip files already loaded.")
def gdelt_raw(context: AssetExecutionContext) -> MaterializeResult:
    from blindspot.ingest.load_gdelt import run

    # One hour of files each run covers a missed schedule tick or two.
    stats = run(float(os.getenv("INGEST_HOURS", "1")), ("export", "mentions"))
    context.log.info(str(stats))
    return MaterializeResult(metadata={k: MetadataValue.int(int(v)) for k, v in stats.items()})


@asset(deps=[gdelt_raw], group_name="transform", description="dbt build: staging, stories, blindspots and tests.")
def dbt_models(context: AssetExecutionContext) -> MaterializeResult:
    out = _run(context, ["dbt", "build", "--profiles-dir", "."], cwd=DBT_DIR)
    done = [line for line in out.splitlines() if "Done." in line]
    return MaterializeResult(metadata={"dbt": MetadataValue.text(done[-1] if done else "ok")})


@asset(deps=[dbt_models], group_name="transform", description="Fails the run if the built tables look wrong.")
def quality_check(context: AssetExecutionContext) -> MaterializeResult:
    out = _run(context, [sys.executable, "-m", "blindspot.quality.check"])
    return MaterializeResult(metadata={"checks": MetadataValue.md(f"```\n{out}\n```")})


@asset(deps=[quality_check], group_name="serve", description="Short summaries of the top stories.")
def story_summaries(context: AssetExecutionContext) -> MaterializeResult:
    from blindspot.summaries.run import run

    stats = run(int(os.getenv("SUMMARY_TOP", "20")), os.getenv("SUMMARY_MODE", "extractive"))
    return MaterializeResult(metadata={k: MetadataValue.int(int(v)) for k, v in stats.items()})


pipeline_job = define_asset_job("blindspot_pipeline", selection="*")

every_15_minutes = ScheduleDefinition(
    job=pipeline_job,
    cron_schedule="*/15 * * * *",
    default_status=DefaultScheduleStatus.RUNNING
    if os.getenv("SCHEDULE_ON", "1") == "1" else DefaultScheduleStatus.STOPPED,
)

defs = Definitions(assets=[gdelt_raw, dbt_models, quality_check, story_summaries],
                   jobs=[pipeline_job], schedules=[every_15_minutes])
