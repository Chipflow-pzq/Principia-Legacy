"""Frozen relevance/latency acceptance cases; supports a separate baseline code tree."""

import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sys
import time


def run(args):
    sys.path.insert(0, str(args.code.resolve() / "src"))
    from principia_legacy.storage import Atlas

    fixture = json.loads(args.queries.read_text())
    outcomes = []
    with closing(Atlas(args.data_home, args.release)) as a:
        for case in fixture["cases"]:
            times = []
            for _ in range(5):
                start = time.perf_counter()
                result = a.search(case["query"], limit=fixture["limit"])
                times.append((time.perf_counter() - start) * 1000)
            if case["category"] == "none":
                ranked = []
                hit = not any(
                    result.get(k) for k in ("results", "people", "works", "topics")
                )
                rank = None
            else:
                ranked = [
                    row.get("name", row.get("title", ""))
                    for row in result.get(case["category"], [])
                ]
                rank = next(
                    (
                        i + 1
                        for i, title in enumerate(ranked)
                        if case["expected"].casefold() in title.casefold()
                    ),
                    None,
                )
                hit = rank is not None
            outcomes.append(
                {
                    **case,
                    "hit": hit,
                    "rank": rank,
                    "top_titles": ranked,
                    "warm_ms": times[1:],
                    "first_query_ms": times[0],
                }
            )
        warm = sorted(v for o in outcomes for v in o["warm_ms"])
        positives = [o for o in outcomes if o["category"] != "none"]
        report = {
            "label": args.label,
            "release_id": a.release,
            "snapshot_hash": a.snapshot_hash,
            "query_fixture_sha256": hashlib.sha256(
                args.queries.read_bytes()
            ).hexdigest(),
            "case_count": len(outcomes),
            "hit_at_10": sum(o["hit"] for o in positives) / len(positives),
            "mrr_at_10": sum(1 / o["rank"] if o["rank"] else 0 for o in positives)
            / len(positives),
            "missing_queries_correct": sum(
                o["hit"] for o in outcomes if o["category"] == "none"
            ),
            "warm_search_p95_ms": warm[int(len(warm) * 0.95)],
            "network_latency_ms": 0,
            "outcomes": outcomes,
            "scope": fixture["scope"],
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print({k: v for k, v in report.items() if k != "outcomes"})


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--code", type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument("--data-home", type=Path, required=True)
    p.add_argument("--queries", type=Path, required=True)
    p.add_argument("--release")
    p.add_argument("--label", required=True)
    p.add_argument("--output", type=Path, required=True)
    run(p.parse_args())
