"""Run a frozen, bounded curriculum campaign through the existing evidence pipeline.

Only completed, validated batches refresh the working reader. Published releases
are untouched. A stop file ends work between batches without discarding receipts.
"""

import argparse
from pathlib import Path
import sys
import subprocess
import os
from contextlib import contextmanager

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "src"))
from principia_legacy.common import (
    digest,
    now,
    read_json,
    read_lines,
    write_json,
    write_lines,
    atomic_write,
)
from principia_legacy.expansion import expand
from principia_legacy.storage import build
from principia_legacy.release import report


@contextmanager
def campaign_lock(identity):
    path = root / ".work" / (identity + ".pid")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            os.kill(int(path.read_text()), 0)
        except ProcessLookupError:
            path.unlink()
        else:
            raise ValueError(
                "This campaign is already running; inspect its report instead of starting a duplicate"
            )
    with path.open("x") as handle:
        handle.write(str(os.getpid()))
    try:
        yield
    finally:
        path.unlink(missing_ok=True)


def run(args):
    plan = read_json(root / args.plan)
    identity = plan["id"]
    if not identity.replace("-", "").isalnum():
        raise ValueError("Unsafe campaign identity")
    status_path = root / "reports/campaigns" / (identity + ".json")
    status = read_json(status_path, {})
    if status and status["plan_hash"] != digest(plan):
        raise ValueError(
            "Campaign is frozen; use a new identity for changed assignments"
        )
    batches = (
        plan["batches"][: args.max_batches] if args.max_batches else plan["batches"]
    )
    estimate = {
        "batches": len(batches),
        "source_assignments": sum(len(b["assignments"]) for b in batches),
        "maximum_parallel_requests": min(max(args.workers, 1), 4),
        "spending": "Owner-managed allowance; usage receipts and per-batch estimates are not an exact bill.",
    }
    print(estimate, flush=True)
    if not args.allow_network:
        print("Plan inspection only. Add --allow-network to execute.", flush=True)
        return
    status = status or {
        "id": identity,
        "plan_hash": digest(plan),
        "started_at": now(),
        "completed_batches": [],
    }
    templates = {t["id"]: t for t in plan["topic_templates"]}
    for batch in batches:
        if batch["id"] in status["completed_batches"]:
            continue
        if (root / ".work" / (identity + ".stop")).exists():
            status.update(state="stopped_between_batches", updated_at=now())
            write_json(status_path, status)
            return
        usage = report(root)["usage"]
        status.setdefault("unknown_charge_baseline", usage["unknown_possible_charge"])
        if (
            usage["planning_estimate"]["known_token_subtotal"]
            >= args.pause_estimate_cny
            or usage["unknown_possible_charge"] > status["unknown_charge_baseline"] + 12
        ):
            status.update(
                state="needs_manual_spending_inspection", updated_at=now(), usage=usage
            )
            write_json(status_path, status)
            return
        registry = read_lines(root / "manifests/FRONTIER_REGISTRY.jsonl")
        known = {d["id"] for d in registry}
        for j in batch["assignments"]:
            if j["dossier"] not in known:
                registry.append(templates[j["dossier"]])
                known.add(j["dossier"])
        write_lines(root / "manifests/FRONTIER_REGISTRY.jsonl", registry)
        frozen = {
            **batch,
            "model": plan["model"],
            "new_node_allowance": 24,
            "frozen_checklists": {
                j["dossier"]: templates[j["dossier"]]["checklist"]
                for j in batch["assignments"]
            },
        }
        path = root / "config/plans" / (batch["id"] + ".json")
        old = read_json(path)
        if old and old != frozen:
            raise ValueError("Frozen batch has changed")
        write_json(path, frozen)
        status.update(state="running", active_batch=batch["id"], updated_at=now())
        write_json(status_path, status)
        result = expand(root, path, args.env_file, args.workers)
        # This can only remove padded fragments. It never upgrades a source or
        # claims human review, and changed versions invalidate dependent arrows.
        subprocess.run(
            [
                sys.executable,
                str(root / "scripts/editorial_screen.py"),
                args.env_file,
                "--records-file",
                f"corpus/expansions/{batch['id']}.jsonl",
                "--workers",
                str(args.workers),
                "--apply",
                "--output",
                f"reports/campaigns/{batch['id']}-editorial.json",
            ],
            cwd=root,
            check=True,
        )
        build(root)
        summary = report(root)
        status["completed_batches"].append(batch["id"])
        status.update(
            updated_at=now(),
            counts=summary["counts"],
            coverage=summary["coverage"],
            shortfall_by_subject=summary["shortfall_by_subject"],
            usage=summary["usage"],
        )
        write_json(root / "reports/campaigns" / (identity + "-coverage.json"), summary)
        failed = sum(
            o["state"] in {"failed", "quarantined"}
            or o.get("admission") in {"quarantined", "needs_revision_patch"}
            for o in result["outcomes"]
        )
        status["last_batch_failed_assignments"] = failed
        write_json(status_path, status)
        rows = [
            "# Build status",
            "",
            f"Working expansion updated {now()}. Published releases remain separate immutable snapshots.",
            "",
            "| Subject | Populated topics | Unique insights | Remaining topics / insights |",
            "|---|---:|---:|---:|",
        ]
        for subject, c in summary["coverage"].items():
            gap = summary["shortfall_by_subject"][subject]
            rows.append(
                f"| {subject.replace('_', ' ')} | {c['populated_topics']} | {c['contributions']} | {gap['populated_topics']} / {gap['unique_primary_subject_insights']} |"
            )
        rows += [
            "",
            "Target: at least 200 populated topics and 2,000 unique primary-subject insights per subject. Empty assignments and shared memberships do not inflate these counts.",
            "",
            f"Human review: **{summary['human_reviewed_contributions']} contributions have a recorded human review; qualified independent audit {summary['independent_human_audit']}**. Content is exploratory and machine-screened, with attribution and ancestry gaps retained.",
            "",
            f"Campaign: {len(status['completed_batches'])}/{len(plan['batches'])} batches completed. Current receipts: {summary['usage']['requests']} attempts; {summary['usage']['unknown_possible_charge']} unknown/running possible charges. Token receipts are not a bill; the US$300-equivalent allowance remains owner-managed.",
            f"Known-token planning subtotal: CNY {summary['usage']['planning_estimate']['known_token_subtotal']}; excludes unknown usage and discounts. The runner pauses for manual inspection at CNY {args.pause_estimate_cny} or a large increase in unknown-charge attempts. This is a conservative pause trigger, not exact allowance enforcement.",
            "",
            "Software verification and immutable-release limitations are documented in reports/1.2.0-verification-summary.json and docs/RELEASE-1.2.md. The working expansion has structural validation after each batch; it is not a newly qualified human review or a frozen release.",
            "",
            f"Next bounded work: continue the frozen campaign after {batch['id']}; inspect source failures and duplicate/reuse decisions. Create .work/{identity}.stop to stop between batches.",
        ]
        atomic_write(root / "BUILD_STATUS.md", "\n".join(rows) + "\n")
        print(
            {
                "batch": batch["id"],
                "counts": summary["counts"],
                "failed_assignments": failed,
            },
            flush=True,
        )
        if failed > max(2, len(batch["assignments"]) // 3):
            status.update(state="needs_source_or_provider_inspection", updated_at=now())
            write_json(status_path, status)
            return
    status.update(state="bounded_run_complete", updated_at=now())
    write_json(status_path, status)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--env-file")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument(
        "--pause-estimate-cny",
        type=float,
        default=1000,
        help="Conservative planning pause trigger, not the account bill",
    )
    parser.add_argument(
        "--max-batches", type=int, help="Optional bounded prefix of the frozen campaign"
    )
    args = parser.parse_args()
    if args.allow_network:
        if not args.env_file:
            parser.error("--env-file is required for explicit campaign authoring")
        identity = read_json(root / args.plan)["id"]
        if not identity.replace("-", "").isalnum():
            raise ValueError("Unsafe campaign identity")
        with campaign_lock(identity):
            try:
                run(args)
            except Exception as exc:
                path = root / "reports/campaigns" / (identity + ".json")
                status = read_json(path, {"id": identity})
                status.update(
                    state="failed_needs_inspection",
                    updated_at=now(),
                    error_type=type(exc).__name__,
                )
                write_json(path, status)
                raise
    else:
        run(args)
