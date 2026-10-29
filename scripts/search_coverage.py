"""Report searchable content separately from catalogue-only hits on frozen queries."""

import argparse
import json
import sys
import time
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from principia_legacy.common import digest, now, read_json, write_json
from principia_legacy.storage import Atlas


def run(args):
    fixture = read_json(args.queries)
    outcomes, warm = [], []
    with closing(Atlas(args.data_home, args.release)) as atlas:
        for q in [*fixture["queries"], *fixture["negative_queries"]]:
            times = []
            for _ in range(3):
                start = time.perf_counter()
                result = atlas.search(q, limit=8)
                times.append(round((time.perf_counter() - start) * 1000, 2))
            warm.extend(times[1:])
            content = bool(
                result["results"]
                or any(w.get("insight_count") for w in result["works"])
                or any(
                    atlas.dossier(t["id"])["dossier"]["contribution_count"]
                    for t in result["topics"]
                )
            )
            outcomes.append(
                {
                    "query": q,
                    "negative_control": q in fixture["negative_queries"],
                    "totals": result["totals"],
                    "content_available": content,
                    "match_mode": result.get("search_interpretation", {}).get(
                        "match_mode"
                    ),
                    "timings_ms": times,
                    "top_results": {
                        kind: [
                            {
                                "id": r["id"],
                                "title": r.get("title", r.get("name")),
                                **(
                                    {"insight_count": r["insight_count"]}
                                    if "insight_count" in r
                                    else {}
                                ),
                            }
                            for r in result[kind][:5]
                        ]
                        for kind in ["results", "topics", "works", "people"]
                    },
                }
            )
        positive = [o for o in outcomes if not o["negative_control"]]
        report = atlas.response(
            created_at=now(),
            fixture_sha256=digest(args.queries.read_bytes()),
            scope=fixture["scope"],
            positive_queries=len(positive),
            with_content=sum(o["content_available"] for o in positive),
            catalogue_only=sum(
                any(o["totals"].values()) and not o["content_available"]
                for o in positive
            ),
            no_results=sum(not any(o["totals"].values()) for o in positive),
            negative_controls_empty=sum(
                not any(o["totals"].values()) for o in outcomes if o["negative_control"]
            ),
            warm_p95_ms=sorted(warm)[int(len(warm) * 0.95)],
            network_latency_ms=0,
            outcomes=outcomes,
        )
    write_json(args.output, report)
    print(json.dumps({k: v for k, v in report.items() if k != "outcomes"}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-home", type=Path, required=True)
    parser.add_argument("--release")
    parser.add_argument("--queries", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args())
