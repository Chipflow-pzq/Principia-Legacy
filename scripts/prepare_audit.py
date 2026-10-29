"""Prepare a reproducible audit sample; never manufacture audit judgments."""

import argparse
from collections import Counter, defaultdict
from pathlib import Path
import random
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from principia_legacy.common import now, write_json
from principia_legacy.records import visible
from principia_legacy.storage import Atlas


def stratified(items, count, key):
    groups = defaultdict(list)
    for item in sorted(items, key=lambda r: r["id"]):
        groups[key(item)].append(item)
    rng = random.Random(894103)
    for group in sorted(groups):
        rng.shuffle(groups[group])
    chosen = []
    while len(chosen) < count and any(groups.values()):
        for group in sorted(groups):
            if groups[group] and len(chosen) < count:
                chosen.append(groups[group].pop())
    return chosen


def run(args):
    a = Atlas(args.data_home, args.release)
    try:
        if a.release == "working":
            raise ValueError("Audit sampling requires a frozen release")
        records = a.records
        nodes = [r for r in records if r["type"] == "contribution" and visible(r)]
        edges = [r for r in records if r["type"] == "relation" and visible(r)]
        by_id = {r["id"]: r for r in nodes}
        node_sample = stratified(nodes, 100, lambda r: r["pillar"])
        edge_sample = stratified(
            edges,
            150,
            lambda r: (
                by_id[r["conclusion"]["id"]]["pillar"],
                r["layer"],
                r["predicate"],
            ),
        )
        sample = {
            "release_id": a.release,
            "snapshot_hash": a.snapshot_hash,
            "prepared_at": now(),
            "status": "Prepared; no qualified human audit performed",
            "selection": "Fixed seed 894103; equal subject cycling for insights; subject/layer/predicate cycling for relations; without replacement. Sampling is not a quality verdict.",
            "requested": {"contributions": 100, "relations": 150},
            "actual": {
                "contributions": len(node_sample),
                "relations": len(edge_sample),
            },
            "strata": {
                "contributions_by_subject": dict(
                    Counter(r["pillar"] for r in node_sample)
                ),
                "relations_by_predicate": dict(
                    Counter(r["predicate"] for r in edge_sample)
                ),
            },
            "instructions": [
                "Read each exact record revision and its source anchors.",
                "For an insight assess scope, attribution, support, assumptions and limits.",
                "For a relation assess exact endpoint revisions, predicate, direction, warrant and joint premises independently of endpoint correctness.",
                "Record expertise, uncertainty and disagreement; a software check is not a human judgment.",
            ],
            "items": [
                {
                    "id": r["id"],
                    "revision": r["revision"],
                    "content_hash": r["content_hash"],
                    "type": r["type"],
                    "source_anchors": r["anchors"],
                    "endpoints": [*r["premises"], r["conclusion"]]
                    if r["type"] == "relation"
                    else [],
                    "reviewer": None,
                    "expertise": None,
                    "judgment": None,
                    "rationale": None,
                    "completed_at": None,
                }
                for r in [*node_sample, *edge_sample]
            ],
        }
        write_json(args.output, sample)
        print(sample["actual"])
    finally:
        a.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-home", type=Path, required=True)
    p.add_argument("--release", required=True)
    p.add_argument("--output", type=Path, required=True)
    run(p.parse_args())
