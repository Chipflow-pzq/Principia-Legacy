"""Apply an explicitly selected, completed relation audit through immutable patches.

Unresolved contextual follow-ups remain withheld. Only separately checked repairs
are republished, with new revision-bound machine reviews. No human review implied.
"""

import argparse
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "src"))
from principia_legacy.common import digest, read_json, seal, write_json, write_lines
from principia_legacy.curate import make_review
from principia_legacy.lifecycle import prepare_patch, apply_patch
from principia_legacy.records import PREDICATES, validate
from principia_legacy.storage import corpus, latest_records


def run(args):
    audit, resolution = read_json(root / args.audit), read_json(root / args.resolution)
    if (
        audit["status"] != "complete"
        or resolution["status"] != "complete"
        or resolution["audit_hash"] != digest(audit)
    ):
        raise ValueError("Completed matching audit and resolution required")
    reviews_path = root / "corpus/reviews" / (args.name + ".jsonl")
    if reviews_path.exists():
        raise ValueError("This audit has already been applied")
    current = {r["id"]: r for r in latest_records(corpus(root))}
    for ref in audit["input_refs"]:
        if any(current[ref["id"]][k] != ref[k] for k in ("revision", "content_hash")):
            raise ValueError("An audited record changed; do not apply stale verdicts")
    judgments = {
        c["id"]: (c, b["receipt"]) for b in audit["batches"] for c in b["checks"]
    }
    choices = {r["id"]: (r, b) for b in resolution["batches"] for r in b["resolutions"]}
    if args.context:
        context = read_json(root / args.context)
        if context["audit_hash"] != digest(audit):
            raise ValueError("Contextual follow-up belongs to a different audit")
        choices.update(
            {r["id"]: (r, b) for b in context["batches"] for r in b["resolutions"]}
        )
    needed = {id for id, (j, _) in judgments.items() if j["decision"] != "supported"}
    if set(choices) != needed:
        raise ValueError("Every flagged arrow must have a resolution")
    proposals, bases, reviews, repaired = [], {}, [], {}
    for id, (judgment, receipt) in judgments.items():
        old = current[id]
        if judgment["decision"] == "supported":
            reviews.append(make_review(old, judgment["rationale"], receipt))
            continue
        choice, batch = choices[id]
        if choice["action"] == "retain":
            reviews.append(make_review(old, choice["reason"], batch["receipt"]))
            continue
        candidate = {
            **old,
            "revision": old["revision"] + 1,
            "curation": {**old["curation"], "audit_reason": choice["reason"]},
        }
        if choice["action"] == "repair":
            if choice.get("verification", {}).get(
                "decision"
            ) != "supported" or not batch.get("check_receipt"):
                raise ValueError("Repair lacks a separate evidence check")
            candidate.update(choice["replacement"])
            candidate["layer"] = PREDICATES[candidate["predicate"]][0]
            candidate["anchors"] = choice.get("expanded_anchors", old["anchors"])
            repaired[id] = (choice, batch["check_receipt"])
        elif choice["action"] != "withhold":
            raise ValueError("Unknown action")
        bases[id] = old["content_hash"]
        proposals.append(candidate)
    patch = prepare_patch(
        root,
        {
            "reason": "Source-grounded relation audit: correct type, scope and evidence; withhold unsupported arrows. Historical versions remain reproducible.",
            "base_hashes": bases,
            "records": proposals,
        },
    )
    path = root / "reports" / (args.name + "-patch.json")
    write_json(path, patch)
    additions = []
    for record in patch["records"]:
        if record["id"] not in repaired:
            continue
        choice, receipt = repaired[record["id"]]
        record = {
            **record,
            "revision": record["revision"] + 1,
            "publication_state": "exploratory",
            "machine_screening": "passed",
            "human_review": "not_reviewed",
            "curation": {
                "method": "Explicit typed-arrow correction with separately checked pinned source evidence",
                "screening_request_id": receipt["request_id"],
                "requested_model": receipt["requested_model"],
            },
        }
        seal(record)
        additions.append(record)
        reviews.append(
            make_review(record, choice["verification"]["rationale"], receipt)
        )
    errors = validate([*corpus(root), *patch["records"], *additions, *reviews])
    if errors:
        raise ValueError(errors[:20])
    applied = apply_patch(root, path)
    write_lines(root / "corpus/screenings" / (args.name + ".jsonl"), additions)
    write_lines(reviews_path, reviews)
    write_json(
        root / "reports" / (args.name + "-applied.json"),
        {
            "patch": applied,
            "audited": len(judgments),
            "retained_without_change": len(judgments) - len(proposals),
            "repaired": len(additions),
            "withheld": len(proposals) - len(additions),
            "new_exact_machine_reviews": len(reviews),
            "qualified_human_review": False,
        },
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--audit", required=True)
    p.add_argument("--resolution", required=True)
    p.add_argument("--context")
    p.add_argument("--name", required=True)
    args = p.parse_args()
    if not args.name.replace("-", "").isalnum():
        raise ValueError("Use a simple audit identity")
    run(args)
