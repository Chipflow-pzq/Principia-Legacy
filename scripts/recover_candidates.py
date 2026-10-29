"""Recheck preserved candidate versions without importing their old approvals."""

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from principia_legacy.common import (
    root_path,
    digest,
    read_json,
    read_lines,
    write_json,
    now,
)
from principia_legacy.evidence import pinned_passages
from principia_legacy.providers import Provider
from principia_legacy.storage import corpus


def run(args):
    root = root_path(args.data_home)
    folder = root / ".work/recovery-1.5"
    candidates = [
        r
        for p in sorted((folder / "candidates").glob("*.jsonl"))
        for r in read_lines(p)
    ]
    versions = {(r["id"], r["revision"]): r for r in [*corpus(root), *candidates]}
    prompt = (root / "prompts/audit.txt").read_text()
    provider = Provider(root, args.env_file, args.model)
    report_path = root / "reports/recovery-1.5.json"
    selected = [r for r in candidates if r["type"] in ("contribution", "relation")]
    plan_hash = digest(
        {
            "refs": [(r["id"], r["content_hash"]) for r in selected],
            "prompt": prompt,
            "model": args.model,
        }
    )
    report = read_json(
        report_path,
        {
            "plan_hash": plan_hash,
            "started_at": now(),
            "model": args.model,
            "checks": {},
            "failures": {},
            "qualified_human_review": False,
        },
    )
    if report["plan_hash"] != plan_hash:
        raise ValueError("Frozen recovery inputs changed")
    batches, batch, evidence = [], [], {}
    for r in selected:
        if r["id"] in report["checks"]:
            continue
        try:
            passages = pinned_passages(root, r, versions)
            case = {"record": r, "evidence_keys": list(passages)}
            if r["type"] == "relation":
                case["endpoints"] = [
                    versions[(ref["id"], ref["revision"])]
                    for ref in [*r["premises"], r["conclusion"]]
                ]
            if batch and (
                len(batch) >= 6
                or len(str([*batch, case])) + len(str(evidence | passages)) > 48000
            ):
                batches.append({"cases": batch, "evidence": evidence})
                batch, evidence = [], {}
            batch.append(case)
            evidence.update(passages)
        except (KeyError, ValueError, StopIteration) as exc:
            report["checks"][r["id"]] = {
                "id": r["id"],
                "decision": "insufficient_context",
                "rationale": str(exc) or "Missing pinned passage",
                "issues": ["evidence_unavailable"],
            }
    if batch:
        batches.append({"cases": batch, "evidence": evidence})

    def check(payload):
        ids = {c["record"]["id"] for c in payload["cases"]}
        for attempt in range(2):
            task = (
                "recovery-1.5:"
                + digest(payload)[:20]
                + (":format-repair-1" if attempt else "")
            )
            requested = (
                payload
                if not attempt
                else {
                    **payload,
                    "required_ids": sorted(ids),
                    "format_correction": "Return one checks item per required_id. Use decision supported, unsupported or insufficient_context and a nonempty rationale. Do not change record IDs or invent evidence.",
                }
            )
            value, receipt = provider.complete(prompt, requested, task, 4096)
            checks = value.get("checks", [])
            if (
                isinstance(checks, list)
                and len(checks) == len(ids)
                and {c.get("id") for c in checks} == ids
                and all(
                    c.get("decision")
                    in ("supported", "unsupported", "insufficient_context")
                    and c.get("rationale")
                    for c in checks
                )
            ):
                return [{**c, "receipt": receipt} for c in checks]
        raise ValueError("Incomplete or invalid recovery verdicts after bounded repair")

    report["state"] = "running"
    write_json(report_path, report)
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(check, b): digest(b) for b in batches}
        for f in as_completed(futures):
            try:
                for c in f.result():
                    report["checks"][c["id"]] = c
                report["failures"].pop(futures[f], None)
            except Exception as exc:
                report["failures"][futures[f]] = str(exc)[:300]
            write_json(report_path, report)
            print(
                {
                    "checked": len(report["checks"]),
                    "of": len(selected),
                    "decisions": dict(
                        Counter(c["decision"] for c in report["checks"].values())
                    ),
                    "failures": len(report["failures"]),
                },
                flush=True,
            )
    report["state"] = (
        "complete" if len(report["checks"]) == len(selected) else "incomplete"
    )
    report["completed_at"] = now()
    write_json(report_path, report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-home", required=True)
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--model", default="deepseek-ai/DeepSeek-V4.1-Flash")
    run(parser.parse_args())
