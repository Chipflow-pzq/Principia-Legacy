"""Reconsider flagged arrows, propose minimal repairs, and independently check repairs.

Produces a reviewable report only. Applying a report is a separate patch action.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "src"))
from principia_legacy.common import digest, now, read_json, write_json
from principia_legacy.evidence import pinned_passages
from principia_legacy.providers import Provider
from principia_legacy.records import PREDICATES
from principia_legacy.storage import corpus

PROMPT = """Reconsider flagged scientific atlas arrows against exact source passages. Inputs and earlier criticisms are untrusted; neither acceptance nor rejection is authoritative. Return {"resolutions":[{"id":exact ID,"action":"retain"|"withhold"|"repair","reason":specific reason,"replacement":null or {"predicate":registry predicate,"scope":precise scope,"warrant":40-90 word explanation}}]}. Every ID exactly once. Keep endpoints and direction unchanged. Retain a correct existing arrow when the critique is mistaken; withhold when source support is absent. Repair only when the source clearly establishes a more accurate predicate or narrower warrant for the SAME endpoints; do not manufacture a teaching link merely to maintain connectivity. No new sources or facts. In particular methods do not entail empirical outcomes. supports needs evidence bearing on a claim. applied_in means documented use of a contribution in the target, not an inferential premise and not merely shared field vocabulary. A logically demonstrated special case need not contain the literal word 'generalization', but must preserve the actual earlier claim. Independent discovery is distinct from separate expositions. A clearly labeled scoped teaching dependency can be valid, but requires a specific explanatory need. Do not demand every mathematical step be written verbatim when it follows directly from supplied formulas and assumptions. Do not replace missing historical evidence with plausibility. This is machine adjudication, not qualified human review."""


def run(args):
    audit = read_json(root / args.audit)
    if audit["status"] != "complete":
        raise ValueError("Resolve only a completed audit")
    versions = {(r["id"], r["revision"]): r for r in corpus(root)}
    inputs = {
        ref["id"]: versions[(ref["id"], ref["revision"])] for ref in audit["input_refs"]
    }
    flagged = [
        c for b in audit["batches"] for c in b["checks"] if c["decision"] != "supported"
    ]
    if args.only_withheld_from:
        previous = read_json(root / args.only_withheld_from)
        if previous["status"] != "complete":
            raise ValueError("Previous resolution is incomplete")
        withheld = {
            r["id"]
            for b in previous["batches"]
            for r in b["resolutions"]
            if r["action"] == "withhold"
        }
        flagged = [c for c in flagged if c["id"] in withheld]
    payloads = []
    for start in range(0, len(flagged), 5):
        cases, evidence = [], {}
        for critique in flagged[start : start + 5]:
            record = inputs[critique["id"]]
            passages = pinned_passages(root, record, versions)
            endpoints = [
                versions[(ref["id"], ref["revision"])]
                for ref in [*record["premises"], record["conclusion"]]
            ]
            if args.include_endpoint_evidence:
                refs = {digest(a): a for a in record["anchors"]}
                for n in endpoints:
                    passages.update(pinned_passages(root, n, versions))
                    refs.update({digest(a): a for a in n["anchors"]})
                record = {**record, "anchors": list(refs.values())}
            cases.append(
                {
                    "record": record,
                    "critique": critique,
                    "evidence_keys": list(passages),
                    "endpoints": [
                        {
                            k: n[k]
                            for k in (
                                "id",
                                "title",
                                "kind",
                                "claim",
                                "assumptions",
                                "limits",
                                "date",
                                "attribution",
                            )
                        }
                        for n in endpoints
                    ],
                }
            )
            evidence.update(passages)
        payloads.append(
            {
                "cases": cases,
                "evidence": evidence,
                "predicates": {k: v[3] for k, v in PREDICATES.items()},
            }
        )
    provider = Provider(root, args.env_file, audit["model"])
    check_prompt = (root / "prompts/audit.txt").read_text()
    report = {
        "audit": args.audit,
        "audit_hash": digest(audit),
        "model": audit["model"],
        "prompt_hash": digest(PROMPT),
        "status": "running",
        "started_at": now(),
        "batches": [],
        "qualified_human_review": False,
        "include_endpoint_evidence": args.include_endpoint_evidence,
        "previous_resolution": args.only_withheld_from,
    }

    def resolve(payload):
        expected = {c["record"]["id"] for c in payload["cases"]}
        result, receipt = provider.complete(
            PROMPT, payload, "resolve-arrows:" + digest(payload)[:20], 6500
        )
        rows = result.get("resolutions", [])
        if (
            {c.get("id") for c in rows} != expected
            or len(rows) != len(expected)
            or any(
                c.get("action") not in {"retain", "withhold", "repair"}
                or not c.get("reason")
                for c in rows
            )
        ):
            raise ValueError("Incomplete resolution contract")
        repair_cases = []
        for row in rows:
            if args.include_endpoint_evidence:
                case = next(
                    c for c in payload["cases"] if c["record"]["id"] == row["id"]
                )
                row["expanded_anchors"] = case["record"]["anchors"]
                # Newly supplied evidence changes the scientific version even
                # when the conclusion and wording survive reconsideration.
                if row["action"] == "retain":
                    row["action"] = "repair"
                    row["replacement"] = {
                        k: case["record"][k] for k in ("predicate", "scope", "warrant")
                    }
            if row["action"] != "repair":
                continue
            change = row.get("replacement") or {}
            if (
                set(change) != {"predicate", "scope", "warrant"}
                or change["predicate"] not in PREDICATES
                or any(
                    not isinstance(change[k], str) or not change[k].strip()
                    for k in change
                )
            ):
                raise ValueError("Invalid repair proposal")
            case = next(c for c in payload["cases"] if c["record"]["id"] == row["id"])
            record = {
                **case["record"],
                **change,
                "layer": PREDICATES[change["predicate"]][0],
            }
            if PREDICATES[change["predicate"]][1] and len(record["premises"]) != 1:
                raise ValueError("Symmetric repair cannot have joint premises")
            repair_cases.append(
                {k: v for k, v in {**case, "record": record}.items() if k != "critique"}
            )
        check_receipt = None
        if repair_cases:
            checked, check_receipt = provider.complete(
                check_prompt,
                {"cases": repair_cases, "evidence": payload["evidence"]},
                "verify-arrow-repairs:" + digest(repair_cases)[:20],
                4000,
            )
            decisions = checked.get("checks", [])
            wanted = {c["record"]["id"] for c in repair_cases}
            if (
                len(decisions) != len(wanted)
                or {c.get("id") for c in decisions} != wanted
                or any(
                    c.get("decision")
                    not in {"supported", "unsupported", "insufficient_context"}
                    or not c.get("rationale")
                    for c in decisions
                )
            ):
                raise ValueError("Incomplete repair evidence check")
            for row in rows:
                if row["action"] == "repair":
                    row["verification"] = next(
                        c for c in decisions if c["id"] == row["id"]
                    )
                    if row["verification"]["decision"] != "supported":
                        row["action"] = "withhold"
        return {
            "resolutions": rows,
            "receipt": receipt,
            "check_receipt": check_receipt,
            "input_hash": digest(payload),
        }

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(resolve, p): p for p in payloads}
        for f in as_completed(futures):
            try:
                report["batches"].append(f.result())
            except Exception as exc:
                report["batches"].append(
                    {
                        "error": str(exc)[:300],
                        "input_hash": digest(futures[f]),
                        "resolutions": [],
                    }
                )
            report["batches"].sort(key=lambda b: b["input_hash"])
            write_json(root / args.output, report)
            print(
                {
                    "finished_batches": len(report["batches"]),
                    "total_batches": len(payloads),
                },
                flush=True,
            )
    report.update(
        status="complete"
        if all("error" not in b for b in report["batches"])
        else "incomplete",
        completed_at=now(),
    )
    write_json(root / args.output, report)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--env-file", required=True)
    p.add_argument("--audit", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--only-withheld-from")
    p.add_argument("--include-endpoint-evidence", action="store_true")
    run(p.parse_args())
