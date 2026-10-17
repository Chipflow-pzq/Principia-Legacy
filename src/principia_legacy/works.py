"""Versioned works and explicit many-to-many reading memberships.

A work is a paper, book, result or technology. A Source is the particular
inspectable evidence version. Being explained by a work never grants discovery
credit to every author of that work, and sharing an insight is not influence.
"""

from collections import defaultdict
from urllib.parse import urlparse

from .common import digest
from .records import PILLARS, PREDICATES, visible


def provenance(sources):
    if not sources:
        raise ValueError("Catalog records require documentary provenance")
    for source in sources:
        url = urlparse(source.get("url", ""))
        if (
            url.scheme != "https"
            or not url.hostname
            or url.username
            or url.password
            or not source.get("title")
            or not source.get("note")
        ):
            raise ValueError(
                "Catalog provenance requires an HTTPS URL, title and evidence note"
            )


def compile_works(manifest, nodes, records):
    works, memberships = {}, {}
    topics = {t["id"] for t in manifest["dossiers"]}
    people = {p["id"] for p in manifest.get("people", [])}
    sources = {(s["id"], s["revision"]): s for s in records if s["type"] == "source"}
    snapshot_refs = {r["id"]: r for r in manifest.get("record_refs", [])}
    for raw in manifest.get("works", []):
        work = dict(raw)
        if (
            not work.get("id")
            or work["id"] in works
            or not work.get("title")
            or not work.get("kind")
            or not work.get("summary")
            or not isinstance(work.get("revision"), int)
            or work["revision"] < 1
        ):
            raise ValueError("Work needs a unique stable identity, title and revision")
        if not work.get("subjects") or not set(work["subjects"]) <= set(PILLARS):
            raise ValueError("Work has unknown subjects")
        if not work.get("topic_ids") or not set(work["topic_ids"]) <= topics:
            raise ValueError("Every work must belong to at least one registered topic")
        if not set(work.get("people", [])) <= people:
            raise ValueError("Work credits an undefined individual")
        provenance(work.get("provenance", []))
        for ref in work.get("source_refs", []):
            source = sources.get((ref["id"], ref["revision"]))
            if not source or source["content_hash"] != ref["content_hash"]:
                raise ValueError("Work references a missing evidence version")
        expected = digest({k: v for k, v in work.items() if k != "content_hash"})
        if work.get("content_hash") != expected:
            raise ValueError("Work content hash mismatch: " + work["id"])
        works[work["id"]] = work
    for member in manifest.get("work_insights", []):
        ref, work_id = member["contribution"], member["work_id"]
        if (
            work_id not in works
            or not member.get("reason")
            or member.get("role")
            not in {"establishes", "uses", "explains", "discusses"}
        ):
            raise ValueError(
                "Work-insight membership needs a valid work, role and rationale"
            )
        node = nodes.get(ref["id"])
        if not node or any(node[k] != ref[k] for k in ("revision", "content_hash")):
            continue  # Changed claims never inherit an old interpretive membership.
        work_ref = member.get("work")
        if work_ref and any(
            works[work_id][k] != work_ref[k] for k in ("id", "revision", "content_hash")
        ):
            continue
        stale_source = False
        for anchor in member.get("anchors", []):
            old = sources.get((anchor["source_id"], anchor["source_revision"]))
            active_ref = snapshot_refs.get(anchor["source_id"])
            current = (
                sources.get((anchor["source_id"], active_ref["revision"]))
                if active_ref
                else None
            )
            if old and current and old["revision"] != current["revision"]:
                ignored = {"revision", "content_hash", "anchors", "change_reason"}
                unchanged = {k: v for k, v in old.items() if k not in ignored} == {
                    k: v for k, v in current.items() if k not in ignored
                }
                current_anchors = {a["id"]: a for a in current["anchors"]}
                stale_source |= not unchanged or any(
                    current_anchors.get(a["id"]) != a for a in old["anchors"]
                )
        if stale_source:
            continue
        source_refs = {
            (r["id"], r["revision"]) for r in works[work_id].get("source_refs", [])
        }
        if not member.get("anchors"):
            raise ValueError("Work-insight membership needs evidence anchors")
        for anchor in member["anchors"]:
            source = sources.get((anchor["source_id"], anchor["source_revision"]))
            if (
                not source
                or anchor["anchor_id"] not in {a["id"] for a in source["anchors"]}
                or (anchor["source_id"], anchor["source_revision"]) not in source_refs
            ):
                raise ValueError("Work-insight membership has unresolved provenance")
        if (work_id, ref["id"]) in memberships:
            raise ValueError("Duplicate work-insight membership")
        memberships[(work_id, ref["id"])] = member
    links = []
    link_ids = set()
    projected_pairs = set()
    record_versions = {(r["id"], r["revision"]): r for r in records}
    for raw in manifest.get("work_relations", []):
        link = dict(raw)
        if not link.get("id") or link["id"] in link_ids or link.get("revision", 0) < 1:
            raise ValueError("Work connections need unique stable IDs and revisions")
        link_ids.add(link["id"])
        if link.get("content_hash") != digest(
            {k: v for k, v in link.items() if k != "content_hash"}
        ):
            raise ValueError("Work connection content hash mismatch")
        if link["from"]["id"] == link["to"]["id"]:
            raise ValueError("A work cannot connect to itself")
        if link["predicate"] not in PREDICATES or not link.get("warrant"):
            raise ValueError("Work connection needs a registered predicate and warrant")
        for endpoint in (link["from"], link["to"]):
            w = works.get(endpoint["id"])
            if not w or any(w[k] != endpoint[k] for k in ("revision", "content_hash")):
                break
        else:
            provenance(link.get("provenance", []))
            basis = link.get("basis_relation")
            if not basis:
                raise ValueError(
                    "Work connections require a checked insight relationship as their basis"
                )
            if basis:
                edge = record_versions.get((basis["id"], basis["revision"]))
                if (
                    not edge
                    or snapshot_refs.get(edge["id"]) != basis
                    or not visible(edge)
                ):
                    continue
                if edge["predicate"] != link["predicate"] or len(edge["premises"]) != 1:
                    raise ValueError(
                        "Work projection cannot change its basis predicate or split joint premises"
                    )
                pair = (edge["premises"][0]["id"], edge["conclusion"]["id"])
                if (link["from"]["id"], pair[0]) not in memberships or (
                    link["to"]["id"],
                    pair[1],
                ) not in memberships:
                    continue
            pair = (link["from"]["id"], link["to"]["id"])
            if PREDICATES[link["predicate"]][1]:
                pair = tuple(sorted(pair))
            key = (*pair, link["predicate"], basis["id"])
            if key in projected_pairs:
                raise ValueError(
                    "Duplicate work projection, including reversed symmetric relationships"
                )
            projected_pairs.add(key)
            links.append(link)
    counts = defaultdict(int)
    for work_id, _ in memberships:
        counts[work_id] += 1
    for work_id, work in works.items():
        work["insight_count"] = counts[work_id]
        work["status"] = "insights_available" if counts[work_id] else "catalogued"
    return works, memberships, links
