"""Audit one server snapshot, including private evidence, without copying its data.

Counts and hash checks establish inventory/integrity, not scientific correctness.
The output deliberately separates searchable catalogue entries from explanations.
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from principia_legacy.common import digest, now, read_json, write_json
from principia_legacy.coverage import coverage_report
from principia_legacy.records import visible
from principia_legacy.storage import Atlas


def audit(root, release=None):
    root = Path(root)
    report = coverage_report(root, release)
    with closing(Atlas(root, release)) as atlas:
        records = atlas.records
        nodes = [r for r in records if r["type"] == "contribution" and visible(r)]
        edges = [r for r in records if r["type"] == "relation" and visible(r)]
        sources = {
            (r["id"], r["revision"]): r for r in records if r["type"] == "source"
        }
        reviews = [r for r in records if r["type"] == "review"]
        accepted = {
            r["target"]["content_hash"]
            for r in reviews
            if r["reviewer_type"] == "machine" and r["judgment"] == "accepted"
        }
        caches, evidence_errors = {}, []
        for record in [*nodes, *edges]:
            for ref in record.get("anchors", []):
                key = (ref["source_id"], ref["source_revision"])
                source = sources.get(key)
                if source is None:
                    row = atlas.db.execute(
                        "SELECT payload FROM records WHERE id=? AND revision=? AND type='source'",
                        key,
                    ).fetchone()
                    if row:
                        source = sources[key] = json.loads(row[0])
                if not source:
                    evidence_errors.append(
                        {"id": record["id"], "reason": "source revision missing"}
                    )
                    continue
                if key not in caches:
                    cache = read_json(
                        root / ".work/sources" / (digest(source["url"]) + ".json"), {}
                    )
                    if cache.get("bytes_hash") != source["source_version"]:
                        cache = read_json(
                            root
                            / ".work/sources/history"
                            / (source["source_version"] + ".json"),
                            {},
                        )
                    anchors = {a["id"]: a["text_hash"] for a in source["anchors"]}
                    caches[key] = {
                        p["id"]
                        for p in cache.get("passages", [])
                        if cache.get("bytes_hash") == source["source_version"]
                        and digest(p["text"].encode()) == anchors.get(p["id"])
                    }
                if ref["anchor_id"] not in caches[key]:
                    evidence_errors.append(
                        {
                            "id": record["id"],
                            "anchor": ref,
                            "reason": "private passage missing or hash mismatch",
                        }
                    )
        works = [
            json.loads(r[0])
            for r in atlas.db.execute(
                "SELECT payload FROM works WHERE snapshot=?", (atlas.release,)
            )
        ]
        people = [
            json.loads(r[0])
            for r in atlas.db.execute(
                "SELECT payload FROM people WHERE snapshot=?", (atlas.release,)
            )
        ]
        duplicate_claims = defaultdict(list)
        for node in nodes:
            duplicate_claims[" ".join(node["claim"].lower().split())].append(node["id"])
        for subject, counts in report["subjects"].items():
            ws = [w for w in works if subject in w["subjects"]]
            ps = [p for p in people if subject in p.get("subjects", [])]
            counts.update(
                works=len(ws),
                works_with_insights=sum(bool(w["insight_count"]) for w in ws),
                selected_people=len(ps),
                people_with_insights=sum(bool(p.get("contribution_count")) for p in ps),
                people_with_sourced_profile=sum(
                    bool(p.get("biography") and p.get("bio_sources")) for p in ps
                ),
            )
        report.update(
            audited_at=now(),
            inventory={
                "topics": len(report["topics"]),
                "topics_with_insights": sum(
                    t["insights"] > 0 for t in report["topics"]
                ),
                "route_ready_topics": sum(t["route_ready"] for t in report["topics"]),
                "works": len(works),
                "works_with_insights": sum(bool(w["insight_count"]) for w in works),
                "people": len(people),
                "people_with_insights": sum(
                    bool(p.get("contribution_count")) for p in people
                ),
                "people_with_sourced_profile": sum(
                    bool(p.get("biography") and p.get("bio_sources")) for p in people
                ),
                "source_versions": len(sources),
                "sources_by_access": dict(
                    Counter(s.get("access_state", "unknown") for s in sources.values())
                ),
            },
            integrity={
                "missing_exact_machine_approval": [
                    r["id"]
                    for r in [*nodes, *edges]
                    if r["content_hash"] not in accepted
                ],
                "missing_claim_anchors": [
                    r["id"] for r in [*nodes, *edges] if not r.get("anchors")
                ],
                "missing_limits": [n["id"] for n in nodes if not n.get("limits")],
                "private_evidence_errors": evidence_errors,
                "exact_duplicate_claim_groups": [
                    ids for ids in duplicate_claims.values() if len(ids) > 1
                ],
                "qualified_human_reviews": sum(
                    r["reviewer_type"] == "human" and r["scope"] == "domain_expert"
                    for r in reviews
                ),
                "interpretation": "Exact pins and passages are checked; entailment, attribution and semantic duplication still require independent assessment. Zero integrity errors is not a correctness certificate.",
            },
            incomplete_works=[
                {
                    k: w.get(k)
                    for k in ("id", "title", "subjects", "topic_ids", "provenance")
                }
                for w in works
                if not w["insight_count"]
            ],
            person_depth_notice="A sourced profile and linked works are not a complete biography. No unsourced biography enrichment is inferred.",
            search_scope="A finite curated scientific corpus cannot guarantee a relevant, substantive answer to arbitrary queries; catalogue hits must not be counted as explained answers.",
        )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-home", type=Path, required=True)
    parser.add_argument("--release")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.data_home, args.release)
    write_json(args.output, result)
    print(
        json.dumps(
            {
                "inventory": result["inventory"],
                "integrity": {
                    k: len(v) if isinstance(v, list) else v
                    for k, v in result["integrity"].items()
                },
                "subjects": result["subjects"],
            }
        )
    )
