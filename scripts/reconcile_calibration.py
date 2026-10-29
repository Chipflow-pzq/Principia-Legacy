"""Reassemble already screened calibration records without another model request."""

import argparse
from copy import deepcopy
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from principia_legacy.common import read_json, write_json, now
from principia_legacy.storage import corpus
from principia_legacy.records import validate
from principia_legacy.admission_versions import prepare_versions
from principia_legacy.expansion import admit


def run(root):
    original = read_json(root / ".work/expansion/calibration-1-5-001.json")
    plan = read_json(root / "config/plans/calibration-1-5-001.json")
    plan["id"] = "calibration-1-5-reconciled"
    receipt = {
        "original_plan_hash": original["plan_hash"],
        "started_at": now(),
        "method": "Immutable source-anchor extension; existing scientific identities require patches.",
        "new_model_requests": 0,
        "outcomes": [],
    }
    cached = [(p, read_json(p)) for p in (root / ".work/curated").glob("*.json")]
    for old in original["outcomes"]:
        outcome = deepcopy(old)
        result = outcome.get("result", {})
        if not result.get("records") and outcome.get("state") == "quarantined":
            matches = [
                (p, r)
                for p, r in cached
                if r.get("dossier") == outcome["dossier"]
                and r.get("url") == outcome["url"]
                and r.get("errors") == result.get("errors")
            ]
            if len(matches) != 1:
                outcome["reconciliation_error"] = (
                    "Cannot uniquely resolve preserved quarantine"
                )
                receipt["outcomes"].append(outcome)
                continue
            records = read_json(root / ".work/quarantine" / matches[0][0].name, [])
            if not records:
                outcome["reconciliation_error"] = "Missing quarantined records"
                receipt["outcomes"].append(outcome)
                continue
            result["records"] = records
        existing = corpus(root)
        records, memberships, withheld = prepare_versions(
            existing, result.get("records", []), result.get("reused_memberships", [])
        )
        errors = validate([*existing, *records])
        result.update(records=records, reused_memberships=memberships, errors=errors)
        outcome.update(
            state="quarantined" if errors else "succeeded",
            version_reconciliation=withheld,
        )
        receipt["outcomes"].append(outcome)
    receipt["admission"] = admit(root, plan, receipt["outcomes"])
    receipt["completed_at"] = now()
    write_json(root / ".work/expansion/calibration-1-5-reconciled.json", receipt)
    write_json(
        root / "reports/calibration-1.5-reconciliation.json",
        {
            **{k: v for k, v in receipt.items() if k != "outcomes"},
            "outcomes": [
                {k: v for k, v in o.items() if k != "result"}
                for o in receipt["outcomes"]
            ],
        },
    )
    print(receipt["admission"])


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--data-home", type=Path, required=True)
    run(p.parse_args().data_home)
