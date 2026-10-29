"""Admit the explicitly selected subset of preserved, rechecked candidate records."""

import argparse
from collections import defaultdict
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from principia_legacy.common import read_json, read_lines, write_json, now
from principia_legacy.curate import make_review
from principia_legacy.evidence import pinned_passages
from principia_legacy.expansion import admit
from principia_legacy.storage import corpus


def run(root):
    folder = root / ".work/recovery-1.5"
    candidates = [
        r
        for p in sorted((folder / "candidates").glob("*.jsonl"))
        for r in read_lines(p)
    ]
    versions = {(r["id"], r["revision"]): r for r in [*corpus(root), *candidates]}
    checks = read_json(root / "reports/recovery-1.5.json")["checks"]
    editorial = read_json(root / "reports/editorial-recovery-1.5.json")["decisions"]
    selection = read_json(root / "config/recovery-editorial-1.5.json")
    selected = set(selection["selected_ids"])
    nodes = [
        r for r in candidates if r["type"] == "contribution" and r["id"] in selected
    ]
    if len(nodes) != len(selected):
        raise ValueError("Selection does not resolve uniquely")
    for node in nodes:
        if (
            checks[node["id"]]["decision"] != "supported"
            or editorial[node["id"]]["decision"] != "retain"
        ):
            raise ValueError(
                "A selected candidate did not pass both independent screens"
            )
        pinned_passages(root, node, versions)
    relations = [
        r
        for r in candidates
        if r["type"] == "relation"
        and checks.get(r["id"], {}).get("decision") == "supported"
        and all(ref["id"] in selected for ref in [*r["premises"], r["conclusion"]])
    ]
    for relation in relations:
        pinned_passages(root, relation, versions)
    grouped = defaultdict(list)
    owners = {n["id"]: n["dossiers"][0] for n in nodes}
    for record in [*nodes, *relations]:
        topic = (
            owners[record["id"]]
            if record["type"] == "contribution"
            else owners[record["conclusion"]["id"]]
        )
        check = checks[record["id"]]
        grouped[topic].extend(
            [record, make_review(record, check["rationale"], check["receipt"])]
        )
    templates = {d["id"]: d for d in read_lines(folder / "prior-registry.jsonl")}
    outcomes = []
    for topic, records in grouped.items():
        sources = {
            (a["source_id"], a["source_revision"])
            for r in records
            if r["type"] != "review"
            for a in r["anchors"]
        }
        records.extend(versions[key] for key in sorted(sources))
        outcomes.append(
            {
                "dossier": topic,
                "state": "succeeded",
                "result": {
                    "records": records,
                    "endpoints": [],
                    "roles": {},
                    "gaps": [
                        "Recovered foundational insights; endpoint and a representative route require further source work."
                    ],
                    "search_outcomes": {
                        "alternatives": "Only preserved exact passages rechecked.",
                        "limitations": "Significance and attribution failures withheld in the recovery report.",
                        "attribution": "Exposition is distinct from original discovery; no human audit performed.",
                    },
                },
            }
        )
    plan = {
        "id": "recovery-1-5-admitted",
        "new_node_allowance": 45,
        "topic_templates": [templates[id] for id in sorted(grouped)],
    }
    # Admission validates the union, serializes all writes and preserves versions.
    result = admit(root, plan, outcomes)
    report = {
        "completed_at": now(),
        "qualified_human_review": False,
        "selected_insights": len(nodes),
        "eligible_relations": len(relations),
        "admission": result,
        "outcomes": [{k: v for k, v in o.items() if k != "result"} for o in outcomes],
    }
    write_json(root / "reports/recovery-admission-1.5.json", report)
    print(report)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--data-home", type=Path, required=True)
    run(p.parse_args().data_home)
