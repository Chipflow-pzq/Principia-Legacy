"""Publish aggregate browser acceptance and usage without copying personal maps."""

import argparse
import json
from pathlib import Path


def run(args):
    report = json.loads((args.run / "report.json").read_text())
    if not report.get("finished_at"):
        raise ValueError("Inspect only a completed bounded run")
    prices = {
        "deepseek-ai/DeepSeek-V4.1-Flash": (2, 8),
        "deepseek-ai/DeepSeek-V4-Flash": (3, 9),
        "deepseek-ai/DeepSeek-V4-Pro": (12, 24),
    }
    results = []
    usage = []
    fields = [
        "case",
        "query",
        "model",
        "finished",
        "seconds",
        "first_insight_seconds",
        "first_connection_seconds",
        "nodes",
        "connections",
        "check_status",
        "completion",
        "lineage",
        "structural_target_met",
        "timing_target_met",
        "errors",
        "page_errors",
        "private_input_to_atlas",
        "arrow_inspector",
        "insight_inspector",
        "bundle",
    ]
    for attempt in report["attempts"]:
        results.append({k: attempt.get(k) for k in fields})
        incoming, outgoing = prices[attempt["model"]]
        receipts = attempt.get("receipts", [])
        complete = [
            r
            for r in receipts
            if isinstance(r.get("input_tokens"), int)
            and isinstance(r.get("output_tokens"), int)
        ]
        estimate = (
            sum(
                r["input_tokens"] * incoming + r["output_tokens"] * outgoing
                for r in complete
            )
            / 1_000_000
        )
        usage.append(
            {
                "case": attempt["case"],
                "model": attempt["model"],
                "estimated_cny": round(estimate, 6),
                "submitted_requests": len(attempt.get("requests", [])),
                "receipts": len(receipts),
                "incomplete_receipts": len(receipts) - len(complete),
                "missing_receipts": max(
                    0, len(attempt.get("requests", [])) - len(receipts)
                ),
            }
        )
    output = {
        "date": report["finished_at"],
        "evaluation": "Development acceptance, not a held-out scientific evaluation. All attempted cases retained.",
        "protocol": report["protocol"],
        "base_url": report["base_url"],
        "models": report["requested_models"],
        "results": results,
        "notice": "Structural route criteria are diagnostics, not proof of source support. Preserve original measurements; separately identify subsequent algorithm fixes or qualitative assessments.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    args.usage.write_text(
        json.dumps(
            {
                "not_a_provider_bill": True,
                "known_estimate_cny": round(sum(r["estimated_cny"] for r in usage), 6),
                "attempts": usage,
                "note": "Incomplete or missing receipts remain within the separate CNY300 live-acceptance reservation until explicit reconciliation.",
            },
            indent=2,
        )
        + "\n"
    )
    print(
        {
            "cases": len(results),
            "known_estimate_cny": sum(r["estimated_cny"] for r in usage),
        }
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--usage", type=Path, required=True)
    run(p.parse_args())
