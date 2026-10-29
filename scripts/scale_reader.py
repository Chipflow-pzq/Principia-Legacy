"""Generate isolated synthetic indexes and measure reader queries, never science.

All generated records are explicitly synthetic and live outside canonical data.
The fixture covers broad searches, one large topic and a high-degree profile.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import math
from pathlib import Path
import resource
import statistics
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from principia_legacy.common import seal, write_lines, write_json
from principia_legacy.storage import Atlas, build


def fixture(root, size):
    source = seal(
        {
            "id": "synthetic-source",
            "revision": 1,
            "schema_version": 1,
            "type": "source",
            "title": "SYNTHETIC LOAD FIXTURE — not scientific evidence",
            "creators": ["Synthetic fixture"],
            "url": "https://example.org/synthetic-load-test",
            "source_version": "synthetic-v1",
            "retrieved_at": "2026-10-26",
            "access_state": "anchor_checked",
            "rights": {"license": "CC0 synthetic fixture"},
            "anchors": [
                {
                    "id": "a",
                    "selector": "Synthetic paragraph",
                    "summary": "Synthetic load-test evidence only",
                    "checked": True,
                }
            ],
        }
    )
    subjects = [
        "mathematics",
        "physics",
        "computer_science",
        "economics",
        "biology_medicine",
    ]
    records = [source]
    for i in range(size):
        records.append(
            seal(
                {
                    "id": f"synthetic-{i:06}",
                    "revision": 1,
                    "schema_version": 1,
                    "type": "contribution",
                    "title": f"SYNTHETIC result {i} on mechanism {i % 1000}",
                    "kind": "method",
                    "pillar": subjects[i % 5],
                    "claim": f"Synthetic load fixture: token{i % 1000} identifies a test family; this is not a scientific assertion.",
                    "problem": "Exercise bounded retrieval and pagination with generated test data.",
                    "conceptual_move": "Synthetic variation for reproducible load testing.",
                    "explanation": "This record has no scientific meaning. It tests storage and retrieval under larger datasets. "
                    * 8,
                    "assumptions": ["Synthetic data only"],
                    "limits": ["Not evidence about the world"],
                    "attribution": [
                        {"name": "Synthetic fixture", "role": "test author"}
                    ],
                    "date": {
                        "year": 1900 + i % 125,
                        "precision": "year",
                        "event": "fixture",
                        "note": "Synthetic",
                    },
                    "anchors": [
                        {
                            "source_id": source["id"],
                            "source_revision": 1,
                            "anchor_id": "a",
                        }
                    ],
                    "curation": {"method": "Synthetic load fixture"},
                    "scientific_standing": "synthetic, not empirical",
                    "publication_state": "exploratory",
                    "machine_screening": "passed",
                    "human_review": "not_reviewed",
                    "dossiers": [f"SYN-{i % 5}"],
                }
            )
        )
    for i in range(5, size):
        parent = i % 5 if i % 20 == 0 else i - 5
        records.append(
            seal(
                {
                    "id": f"synthetic-relation-{i:06}",
                    "revision": 1,
                    "schema_version": 1,
                    "type": "relation",
                    "premises": [{"id": f"synthetic-{parent:06}", "revision": 1}],
                    "conclusion": {"id": f"synthetic-{i:06}", "revision": 1},
                    "premise_mode": "all",
                    "predicate": "prerequisite_for_reading",
                    "layer": "pedagogical",
                    "scope": "Synthetic graph fixture only",
                    "warrant": "Synthetic adjacency for load testing, not a scientific inference.",
                    "anchors": [
                        {
                            "source_id": source["id"],
                            "source_revision": 1,
                            "anchor_id": "a",
                        }
                    ],
                    "curation": {"method": "Synthetic fixture"},
                    "publication_state": "exploratory",
                    "machine_screening": "passed",
                    "human_review": "not_reviewed",
                }
            )
        )
    topics = [
        {
            "id": f"SYN-{i}",
            "title": "SYNTHETIC topic " + p,
            "pillar": p,
            "endpoint": f"synthetic-{i:06}",
            "flagship": False,
            "checklist": [],
            "gaps": ["Synthetic test data, no scientific coverage"],
            "status": "populated",
            "tags": ["synthetic"],
            "frontier_open": True,
            "search_outcomes": {},
            "selection_reason": "Load fixture only",
            "backward_search": "Synthetic",
            "boundary_task": "Synthetic",
        }
        for i, p in enumerate(subjects)
    ]
    write_lines(root / "corpus/synthetic.jsonl", records)
    write_lines(root / "manifests/FRONTIER_REGISTRY.jsonl", topics)
    write_json(
        root / "manifests/people.json",
        [
            {
                "id": "synthetic-person",
                "name": "Synthetic fixture",
                "aliases": [],
                "subjects": subjects,
                "biography": "Synthetic high-degree profile, not a real person.",
                "bio_sources": [
                    {
                        "title": "Synthetic",
                        "url": "https://example.org/synthetic-load-test",
                        "note": "Generated fixture, not a biography.",
                    }
                ],
            }
        ],
    )
    write_json(root / "tours/tours.json", [])


def main(args):
    root = Path(args.output).resolve()
    if root.exists() and not args.measure_existing:
        raise ValueError("Choose a fresh isolated fixture directory")
    if args.measure_existing:
        built = {"bytes": (root / "build/atlas.sqlite").stat().st_size}
        compiled = None
    else:
        started = time.perf_counter()
        fixture(root, args.size)
        built = build(root)
        compiled = time.perf_counter() - started

    def request(i):
        t = time.perf_counter()
        a = Atlas(root)
        try:
            if i % 4 == 0:
                value = a.search("synthetic", limit=40)
            elif i % 4 == 1:
                value = a.search(f"token{i % 1000}", limit=40)
            elif i % 4 == 2:
                value = a.neighborhood(dossier=f"SYN-{i % 5}", limit=80)
            else:
                value = a.topic_contributions(
                    f"SYN-{i % 5}", offset=max(0, args.size // 5 - 40)
                )
            return i % 4, (time.perf_counter() - t) * 1000, len(json.dumps(value))
        finally:
            a.close()

    rows = [request(i) for i in range(8)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows.extend(pool.map(request, range(8, 48)))
    metrics = {}
    for key, name in enumerate(
        ["broad_search", "distinct_search", "neighborhood", "last_topic_page"]
    ):
        times = sorted(t for kind, t, _ in rows if kind == key)
        metrics[name] = {
            "p50_ms": statistics.median(times),
            "p95_ms": times[math.ceil(len(times) * 0.95) - 1],
            "samples": len(times),
        }
    report = {
        "synthetic_only": True,
        "fixture_version": 2,
        "size": args.size,
        "compile_seconds": compiled,
        "database_bytes": built["bytes"],
        "concurrency": 4,
        "metrics": metrics,
        "process_peak_rss": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "rss_unit": "bytes" if sys.platform == "darwin" else "KiB",
        "rss_scope": "Reader queries only"
        if args.measure_existing
        else "Includes fixture generation and compilation; not reader-only memory",
        "network_latency_ms": 0,
        "platform": sys.platform,
    }
    write_json(
        root / ("reader-result.json" if args.measure_existing else "result.json"),
        report,
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True)
    p.add_argument("--size", type=int, choices=[10000, 50000, 100000], required=True)
    p.add_argument("--measure-existing", action="store_true")
    main(p.parse_args())
