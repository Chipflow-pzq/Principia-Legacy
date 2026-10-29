"""Run explicit frozen batches sequentially; never replay an uncertain request."""

import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from build_work_catalog import compile_catalog

from principia_legacy.authoring_store import Commit, recover, writer
from principia_legacy.common import digest, now, read_json, write_json
from principia_legacy.expansion import expand
from principia_legacy.storage import build


def run(args):
    root = args.data_home.resolve()
    config = read_json(root / "config/provider_budget.json")
    path = root / "reports" / ("campaign-1.5-" + digest(args.plans)[:12] + ".json")
    progress = read_json(path, {"started_at": now(), "batches": []})
    for name in args.plans:
        if name != Path(name).name or not name.endswith(".json"):
            raise ValueError("Pass frozen plan filenames, not paths")
        with sqlite3.connect(root / ".work/coordination.sqlite") as db:
            exposure, unknown = db.execute(
                "SELECT COALESCE(SUM(COALESCE(estimate,reserved)),0),COALESCE(SUM(CASE WHEN state='unknown' THEN reserved ELSE 0 END),0) FROM charges"
            ).fetchone()
        if exposure >= config["working_ceiling_cny"] * 0.85 or unknown >= config.get(
            "uncertain_exposure_pause_cny", 100
        ):
            progress.update(
                state="paused_for_spending_inspection",
                exposure_cny=exposure,
                unknown_reserved_cny=unknown,
            )
            write_json(path, progress)
            return
        result = expand(root, root / "config/plans" / name, args.env_file, workers=4)
        summary = {
            "plan": name,
            "completed_at": now(),
            "admission": result["admission"],
            "failed": sum(o["state"] == "failed" for o in result["outcomes"]),
            "assignments": len(result["outcomes"]),
        }
        progress["batches"] = [b for b in progress["batches"] if b["plan"] != name] + [
            summary
        ]
        progress.update(state="compiling", updated_at=now())
        write_json(path, progress)
        try:
            with writer(root):
                recover(root)
                commit = Commit(root, "catalog-after:" + name)
                compile_catalog(root, commit)
                commit.publish()
            compiled = None if args.no_build else build(root)
        except Exception as error:
            progress.update(
                state="compilation_failed",
                error=f"{type(error).__name__}: {error}",
                updated_at=now(),
            )
            write_json(path, progress)
            raise
        if compiled:
            progress["compiled_bytes"] = compiled["bytes"]
        else:
            progress["activation"] = (
                "Canonical admissions only; serving the previous immutable snapshot until explicit build."
            )
        if summary["failed"] > summary["assignments"] / 2:
            progress["state"] = "paused_for_failure_inspection"
            write_json(path, progress)
            return
        progress["state"] = "between_batches"
        write_json(path, progress)
    progress.update(state="bounded_campaign_complete", completed_at=now())
    write_json(path, progress)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-home", type=Path, required=True)
    p.add_argument("--env-file", required=True)
    p.add_argument(
        "--no-build",
        action="store_true",
        help="Keep the active reader snapshot unchanged during authoring",
    )
    p.add_argument("plans", nargs="+")
    run(p.parse_args())
