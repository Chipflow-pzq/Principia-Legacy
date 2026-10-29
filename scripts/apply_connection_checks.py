"""Apply one explicitly selected connection check through the correction journal.

Unsupported and unresolved arrows leave browsing; previous snapshots survive.
This command cannot repair or silently relabel an arrow, or claim human review.
"""

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from principia_legacy.common import read_json, read_lines, write_json, digest
from principia_legacy.storage import corpus, latest_records
from principia_legacy.lifecycle import prepare_patch, _apply_patch
from principia_legacy.authoring_store import writer, recover, Commit


def run(args):
    root = args.data_home.resolve()
    report_path = root / "reports/expansion" / (args.batch + "-escalation.json")
    report = read_json(report_path)
    selected = {
        r["id"]: r
        for r in read_lines(root / "corpus/expansions" / (args.batch + ".jsonl"))
        if r["type"] == "relation"
    }
    checks = {c["id"]: c for c in report["checks"]}
    if len(checks) != len(report["checks"]) or set(checks) != set(selected):
        raise ValueError("Every original connection must have exactly one check")
    overrides = read_json(args.overrides, {}) if args.overrides else {}
    if not set(overrides) <= set(checks) or not all(
        isinstance(reason, str) and reason.strip() for reason in overrides.values()
    ):
        raise ValueError("Editorial exclusions require known IDs and explicit reasons")
    output = root / "reports/expansion" / (args.batch + "-correction.json")
    if output.exists():
        raise ValueError("Correction already recorded; inspect it before further work")
    with writer(root):
        recover(root)
        current = {r["id"]: r for r in latest_records(corpus(root))}
        if any(
            current[id]["content_hash"] != r["content_hash"]
            for id, r in selected.items()
        ):
            raise ValueError("A checked connection changed; assess the new revision")
        rejected = {
            id: overrides.get(id, c["rationale"])
            for id, c in checks.items()
            if c["decision"] != "supported" or id in overrides
        }
        applied = None
        commit = Commit(root, "connection-check:" + args.batch)
        if rejected:
            patch = prepare_patch(
                root,
                {
                    "reason": "Stricter source and predicate screening: withhold unsupported or unresolved cross-work arrows; no inferred replacement or human approval.",
                    "base_hashes": {id: current[id]["content_hash"] for id in rejected},
                    "records": [
                        {
                            **current[id],
                            "revision": current[id]["revision"] + 1,
                            "curation": {
                                **current[id]["curation"],
                                "recheck_reason": reason,
                                "check_report_hash": digest(report),
                            },
                        }
                        for id, reason in rejected.items()
                    ],
                },
            )
            path = root / "reports/expansion" / (args.batch + "-correction-patch.json")
            write_json(path, patch)
            applied = _apply_patch(root, path, commit)
        result = {
            "batch": args.batch,
            "check_report_hash": digest(report),
            "retained": len(selected) - len(rejected),
            "withheld": len(rejected),
            "reasons": rejected,
            "patch": applied,
            "human_review": "not performed",
        }
        commit.json(output, result)
        commit.publish()
    print({k: v for k, v in result.items() if k not in {"reasons", "patch"}})


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-home", type=Path, required=True)
    p.add_argument("--batch", required=True)
    p.add_argument(
        "--overrides",
        type=Path,
        help="Explicit assistant editorial exclusions, not human review",
    )
    a = p.parse_args()
    if not a.batch.replace("-", "").isalnum():
        raise ValueError("Invalid batch identity")
    run(a)
