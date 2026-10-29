"""Bounded, resumable evidence review. Produces a report; never silently edits records."""

import argparse
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "src"))
from principia_legacy.common import digest, now, read_json, read_lines, write_json
from principia_legacy.evidence import pinned_passages
from principia_legacy.providers import Provider
from principia_legacy.records import visible
from principia_legacy.storage import corpus, latest_records


def run(args):
    root = (
        args.data_home.resolve()
        if args.data_home
        else Path(__file__).resolve().parents[1]
    )
    history = corpus(root)
    versions = {(r["id"], r["revision"]): r for r in history}
    records = [
        r for r in latest_records(history) if r["type"] == args.kind and visible(r)
    ]
    if args.records_file:
        ids = {r["id"] for r in read_lines(root / args.records_file)}
        records = [r for r in records if r["id"] in ids]
    if args.sample:
        groups = defaultdict(list)
        for r in records:
            subject = (
                r.get("pillar")
                or versions[(r["conclusion"]["id"], r["conclusion"]["revision"])][
                    "pillar"
                ]
            )
            groups[subject].append(r)
        for group in groups.values():
            group.sort(key=lambda r: digest({"seed": "atlas-1-3-audit", "id": r["id"]}))
        records = []
        while len(records) < args.sample and any(groups.values()):
            for subject in sorted(groups):
                if groups[subject] and len(records) < args.sample:
                    records.append(groups[subject].pop())
    selected = [{k: r[k] for k in ("id", "revision", "content_hash")} for r in records]
    prompt = (root / "prompts/audit.txt").read_text()
    batches, cases, evidence, missing = [], [], {}, []
    for record in records:
        try:
            passages = pinned_passages(root, record, versions)
            case = {
                "record": {
                    k: v
                    for k, v in record.items()
                    if k not in {"curation", "human_review", "machine_screening"}
                },
                "evidence_keys": list(passages),
            }
            if args.kind == "relation":
                case["endpoints"] = [
                    {
                        k: n[k]
                        for k in (
                            "id",
                            "title",
                            "kind",
                            "claim",
                            "assumptions",
                            "limits",
                            "attribution",
                            "date",
                        )
                    }
                    for n in [
                        versions[(ref["id"], ref["revision"])]
                        for ref in [*record["premises"], record["conclusion"]]
                    ]
                ]
            combined = {**evidence, **passages}
            if cases and (
                len(cases) >= 12
                or len(str([*cases, case])) + len(str(combined)) > 65000
            ):
                batches.append({"cases": cases, "evidence": evidence})
                cases, evidence = [], {}
            cases.append(case)
            evidence.update(passages)
        except (KeyError, ValueError, StopIteration) as exc:
            missing.append(
                {
                    "id": record["id"],
                    "decision": "insufficient_context",
                    "rationale": str(exc) or "Missing anchor",
                    "issues": ["evidence_unavailable"],
                }
            )
    if cases:
        batches.append({"cases": cases, "evidence": evidence})
    plan = {"model": args.model, "prompt_hash": digest(prompt), "input_refs": selected}
    output = root / args.output
    old = read_json(output, {})
    if old and old.get("plan_hash") != digest(plan):
        raise ValueError("Audit inputs changed; use a new output path")
    if old.get("status") == "complete":
        print("Completed audit retained; no paid requests submitted.")
        return
    report = {
        **plan,
        "plan_hash": digest(plan),
        "started_at": old.get("started_at", now()),
        "kind": args.kind,
        "selection": "all visible records"
        if not args.sample
        else "fixed hash order, equal subject cycling, without replacement",
        "status": "running",
        "qualified_human_review": False,
        "missing_evidence": missing,
        "batches": [],
    }
    provider = Provider(root, args.env_file, args.model)

    def check(payload):
        expected = {c["record"]["id"] for c in payload["cases"]}
        try:
            attempts = []
            for attempt in range(3):
                task = (
                    "atlas-audit:"
                    + digest(payload)[:20]
                    + (f":format-repair-{attempt}" if attempt else "")
                )
                requested = (
                    payload
                    if not attempt
                    else {
                        **payload,
                        "required_ids": sorted(expected),
                        "format_correction": "Return exactly one check per required ID, no extra IDs. Previous contract was incomplete or misidentified.",
                    }
                )
                result, receipt = provider.complete(prompt, requested, task, 5000)
                attempts.append(receipt)
                checks = result.get("checks", [])
                ids = [c.get("id") for c in checks]
                if (
                    len(ids) == len(set(ids))
                    and set(ids) == expected
                    and all(
                        c.get("decision")
                        in {"supported", "unsupported", "insufficient_context"}
                        and c.get("rationale")
                        for c in checks
                    )
                ):
                    return {
                        "input_hash": digest(payload),
                        "checks": checks,
                        "receipt": receipt,
                        "attempts": attempts,
                    }
            raise ValueError(
                "Incomplete or misidentified verdicts after two format repairs"
            )
        except Exception as exc:
            return {
                "input_hash": digest(payload),
                "checks": [],
                "error": str(exc)[:300],
                "ids": sorted(expected),
            }

    with ThreadPoolExecutor(max_workers=4) as pool:
        for future in as_completed(
            [pool.submit(check, payload) for payload in batches]
        ):
            report["batches"].append(future.result())
            report["batches"].sort(key=lambda b: b["input_hash"])
            report["counts"] = dict(
                Counter(c["decision"] for b in report["batches"] for c in b["checks"])
            )
            write_json(output, report)
            print(
                {
                    "finished_batches": len(report["batches"]),
                    "total_batches": len(batches),
                    **report["counts"],
                },
                flush=True,
            )
    report.update(
        status="complete"
        if all("error" not in b for b in report["batches"])
        else "incomplete",
        completed_at=now(),
    )
    write_json(output, report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--data-home", type=Path)
    parser.add_argument("--kind", choices=["contribution", "relation"], required=True)
    parser.add_argument("--records-file", help="Audit a bounded admitted batch")
    parser.add_argument("--sample", type=int, default=0)
    parser.add_argument("--model", default="deepseek-ai/DeepSeek-V4.1-Flash")
    parser.add_argument("--output", required=True)
    run(parser.parse_args())
