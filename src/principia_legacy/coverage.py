"""Snapshot-pinned coverage and structural route candidates, never human review."""

from collections import Counter, defaultdict, deque
from contextlib import closing
from .common import now
from .records import PILLARS, visible
from .storage import Atlas


def assessed_route(topic, assessment, members, relations):
    """One revision-bound readiness rule for reports and the reader."""
    nodes = {n["id"]: n for n in members}
    edges = {r["id"]: r for r in relations}
    core = set(assessment.get("core_insight_ids", []))
    selected = set(assessment.get("relation_ids", []))
    foundations = set(assessment.get("foundational_insight_ids", []))
    pins = assessment.get("record_hashes", {})
    current = {**nodes, **edges}
    ready = bool(
        assessment.get("outcome") == "representative_route_supported"
        and assessment.get("rationale")
        and assessment.get("limitations")
        and assessment.get("endpoint") == topic.get("endpoint")
        and topic.get("endpoint") in core
        and len(core) >= 8
        and core <= nodes.keys()
        and len(selected) >= 3
        and selected <= edges.keys()
        and foundations
        and foundations <= core
        and set(pins) == core | selected
        and all(
            current.get(id, {}).get("content_hash") == value
            for id, value in pins.items()
        )
        and topic.get("gaps")
        and all(n.get("limits") for n in members)
    )
    if ready:
        neighbors = defaultdict(set)
        for id in selected:
            refs = [*edges[id]["premises"], edges[id]["conclusion"]]
            ids = {ref["id"] for ref in refs}
            if not ids <= core or any(
                nodes[ref["id"]]["revision"] != ref["revision"] for ref in refs
            ):
                ready = False
                break
            for node in ids:
                neighbors[node].update(ids - {node})
        connected, queue = {topic["endpoint"]}, deque([topic["endpoint"]])
        while queue:
            for child in neighbors[queue.popleft()] - connected:
                connected.add(child)
                queue.append(child)
        ready = ready and core <= connected
    return {
        "ready": bool(ready),
        "review": "machine_editorial" if ready else "not_assessed_or_incomplete",
        "scope": assessment.get("reading_scope", "") if ready else "",
        "rationale": assessment.get("rationale", "") if ready else "",
        "notice": "Machine assessment of an explanatory reading route; not human review or proof of historical influence.",
    }


def coverage_report(root, release=None):
    with closing(Atlas(root, release)) as a:
        nodes = {n["id"]: n for n in a.contributions() if visible(n)}
        edges = [
            r
            for r in a.records
            if r["type"] == "relation"
            and visible(r)
            and all(
                p["id"] in nodes and nodes[p["id"]]["revision"] == p["revision"]
                for p in [*r["premises"], r["conclusion"]]
            )
        ]
        neighbors = defaultdict(set)
        by_topic = defaultdict(list)
        memberships = defaultdict(set)
        owners = defaultdict(set)
        for topic, id in a.db.execute(
            "SELECT topic,id FROM topic_members WHERE snapshot=?", (a.release,)
        ):
            memberships[topic].add(id)
            owners[id].add(topic)
        cross_subject = []
        for r in edges:
            ids = {p["id"] for p in [*r["premises"], r["conclusion"]]}
            for id in ids:
                neighbors[id].update(ids - {id})
            if len({nodes[id]["pillar"] for id in ids}) > 1:
                cross_subject.append(r["id"])
            for topic in set.intersection(*(owners[id] for id in ids)):
                by_topic[topic].append(r)
        assessments = a.manifest.get("route_assessments", [])
        assessed = {r["topic"]: r for r in assessments}
        topics = []
        for d in a.dossiers()["dossiers"]:
            ids, endpoint = memberships[d["id"]], d.get("endpoint")
            topic_neighbors = defaultdict(set)
            for relation in by_topic[d["id"]]:
                endpoints = {
                    ref["id"] for ref in [*relation["premises"], relation["conclusion"]]
                }
                for id in endpoints:
                    topic_neighbors[id].update(endpoints - {id})
            component = {endpoint} if endpoint in ids else set()
            queue = deque(component)
            while queue:
                for child in topic_neighbors[queue.popleft()] - component:
                    component.add(child)
                    queue.append(child)
            relations = [
                r
                for r in by_topic[d["id"]]
                if r["conclusion"]["id"] in component
                and all(p["id"] in component for p in r["premises"])
            ]
            limits = bool(d.get("gaps")) and all(nodes[id].get("limits") for id in ids)
            structural = (
                len(ids) >= 8
                and endpoint in ids
                and len(component) >= 8
                and len(relations) >= 3
                and limits
            )
            ready = (
                structural
                and assessed_route(
                    d,
                    assessed.get(d["id"], {}),
                    [nodes[id] for id in ids],
                    by_topic[d["id"]],
                )["ready"]
            )
            topics.append(
                {
                    "id": d["id"],
                    "title": d["title"],
                    "subject": d["pillar"],
                    "insights": len(ids),
                    "endpoint": endpoint,
                    "endpoint_component": len(component),
                    "complete_relations": len(relations),
                    "structural_route_candidate": bool(structural),
                    "route_ready": ready,
                    "route_review_state": "machine_editorial"
                    if ready
                    else "not_assessed_or_incomplete",
                    "gaps": d.get("gaps", []),
                    "layers": dict(Counter(r["layer"] for r in relations)),
                }
            )
        subjects = {}
        for subject in PILLARS:
            selected = [d for d in topics if d["subject"] == subject]
            counts = {
                "registered_topics": len(selected),
                "topics_with_content": sum(d["insights"] > 0 for d in selected),
                "topics_with_eight_insights": sum(d["insights"] >= 8 for d in selected),
                "structural_route_candidates": sum(
                    d["structural_route_candidate"] for d in selected
                ),
                "route_ready_topics": sum(d["route_ready"] for d in selected),
                "unique_primary_subject_insights": sum(
                    n["pillar"] == subject for n in nodes.values()
                ),
            }
            counts["shortfall"] = {
                "route_ready_topics": max(0, 100 - counts["route_ready_topics"]),
                "insights": max(0, 1000 - counts["unique_primary_subject_insights"]),
            }
            subjects[subject] = counts
        return a.response(
            created_at=now(),
            target={
                "route_ready_topics_per_subject": 100,
                "insights_per_subject": 1000,
            },
            longer_term_target={
                "topics_per_subject": 200,
                "insights_per_subject": 2000,
            },
            subjects=subjects,
            topics=topics,
            counts={
                "insights": len(nodes),
                "relations": len(edges),
                "isolated_insights": sum(not neighbors[id] for id in nodes),
                "cross_subject_relations": len(cross_subject),
                "joint_premise_relations": sum(len(r["premises"]) > 1 for r in edges),
            },
            cross_subject_relation_ids=cross_subject,
            human_audit="Not performed",
            scope="Structural candidates count complete joint-premise relations and an endpoint-connected component, not historical ancestry or pedagogical sufficiency. Route readiness also requires a current, pinned editorial assessment. All current editorial work is machine work.",
        )
