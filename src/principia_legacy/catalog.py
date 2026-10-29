"""Snapshot-pinned navigation indexes, separate from scientific claim records.

A topic membership says where to read an insight, not who influenced whom.
Contributor profiles project recorded credit; only explicit aliases join names.
"""

import re
import unicodedata
from collections import defaultdict
from urllib.parse import urlparse

from .common import digest
from .records import visible


def name_key(name):
    return " ".join(
        re.findall(
            r"[^\W_]+", unicodedata.normalize("NFKD", name).casefold(), re.UNICODE
        )
    )


def contributor_id(name):
    return "person-" + digest(name_key(name))[:16]


def navigation_index(manifest, records, source_versions=None):
    sources = {
        (r["id"], r["revision"]): r
        for r in (source_versions if source_versions is not None else records)
        if r["type"] == "source"
    }
    active_sources = {r["id"]: r["revision"] for r in records if r["type"] == "source"}
    nodes = {r["id"]: r for r in records if r["type"] == "contribution" and visible(r)}
    topics = {d["id"]: d for d in manifest["dossiers"]}
    memberships = {}
    for n in nodes.values():
        for topic in n.get("dossiers", []):
            if topic in topics:
                memberships[(topic, n["id"])] = {
                    "origin": "record",
                    "reason": "Included in the source-screened contribution record.",
                }
    for m in manifest.get("topic_memberships", []):
        ref = m["contribution"]
        n = nodes.get(ref["id"])
        if m["topic_id"] not in topics:
            raise ValueError("Navigation membership names an unknown topic")
        # A correction invalidates navigation interpretations pinned to old content.
        if (
            not n
            or n["revision"] != ref["revision"]
            or n["content_hash"] != ref["content_hash"]
        ):
            continue
        if not m.get("reason", "").strip():
            raise ValueError("Shared topic membership requires an explanatory reason")
        for anchor in m.get("anchors", []):
            source = sources.get((anchor["source_id"], anchor["source_revision"]))
            if not source or anchor["anchor_id"] not in {
                a["id"] for a in source["anchors"]
            }:
                raise ValueError(
                    "Shared topic membership has an unresolved source anchor"
                )
        from .records import source_anchor_enrichment

        if any(
            active_sources.get(a["source_id"]) != a["source_revision"]
            and not source_anchor_enrichment(
                sources.get((a["source_id"], a["source_revision"])),
                sources.get((a["source_id"], active_sources.get(a["source_id"]))),
            )
            for a in m.get("anchors", [])
        ):
            continue  # A changed supporting source requires a fresh navigation check.
        memberships[(m["topic_id"], n["id"])] = {
            "origin": "machine_screened_navigation"
            if m.get("screening_request_id")
            else "editorial_navigation",
            "reason": m["reason"],
        }
    aliases, profiles, links = {}, {}, {}
    for p in manifest.get("people", []):
        if not p.get("id") or not p.get("name"):
            raise ValueError("Contributor profile requires identity and name")
        if manifest.get("catalog_version", 1) >= 2 and (
            p["name"].count(",") > 1
            or ";" in p["name"]
            or " and " in p["name"]
            or " et al" in p["name"]
        ):
            raise ValueError(
                "Contributor profiles must identify one individual, not an author list"
            )
        if p["id"] in profiles:
            raise ValueError("Duplicate contributor identity")
        if p.get("biography") and not p.get("bio_sources"):
            raise ValueError("Biographical descriptions require sources")
        if manifest.get("catalog_version", 1) >= 2 and (
            p.get("kind") != "person"
            or not p.get("selection_reason")
            or not p.get("bio_sources")
        ):
            raise ValueError(
                "Curated contributors need an individual identity, selection reason and sources"
            )
        for source in p.get("bio_sources", []):
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
                    "Biography requires an inspectable HTTPS source and evidence note"
                )
        for alias in [p["name"], *p.get("aliases", [])]:
            key = name_key(alias)
            if key in aliases and aliases[key] != p["id"]:
                raise ValueError("Ambiguous contributor alias: " + alias)
            aliases[key] = p["id"]
        profiles[p["id"]] = dict(p)
    groups = defaultdict(list)
    for group in manifest.get("credit_groups", []):
        if not group.get("source_ids"):
            raise ValueError(
                "Collective credit expansion must identify its documentary sources"
            )
        groups[name_key(group["credit"])].append(group)
    unknown = {
        "collective",
        "unknown",
        "unspecified",
        "not specified",
        "unknown contributors",
        "various",
        "anonymous",
        "source authors",
        "various authors",
        "collective scientific knowledge",
        "economists collective",
    }
    for n in nodes.values():
        for credit in n["attribution"]:
            name = credit["name"].strip()
            key = name_key(name)
            if key in unknown or not key:
                continue
            documented_groups = [
                g
                for g in groups.get(key, [])
                if set(g["source_ids"]) & {a["source_id"] for a in n["anchors"]}
            ]
            ids = sorted({id for g in documented_groups for id in g["people"]}) or [
                aliases.get(key, contributor_id(name))
            ]
            for id in ids:
                if manifest.get("catalog_version", 1) >= 2 and id not in profiles:
                    continue  # A source author-list string is not a person.
                if documented_groups and id not in profiles:
                    raise ValueError("Credit group links an undefined contributor")
                profiles.setdefault(
                    id,
                    {
                        "id": id,
                        "name": name,
                        "aliases": [],
                        "kind": "attribution",
                        "biography": "",
                        "bio_sources": [],
                    },
                )
                links[(id, n["id"])] = {
                    "role": credit["role"],
                    "evidence_note": credit.get("evidence_note", ""),
                    "recorded_name": name,
                }
    by_person = defaultdict(list)
    for (person, node), credit in links.items():
        by_person[person].append(nodes[node])
    node_topics = defaultdict(set)
    for topic, node in memberships:
        node_topics[node].add(topic)
    result = {}
    for id, p in profiles.items():
        linked = by_person[id]
        related_topics = sorted(
            {topic for n in linked for topic in node_topics[n["id"]]}
            | {
                topic
                for w in manifest.get("works", [])
                if id in w.get("people", [])
                for topic in w["topic_ids"]
            }
        )
        if not linked and not p.get("biography"):
            continue
        values = {
            **p,
            "contribution_count": len(linked),
            "topic_ids": related_topics,
            "subjects": sorted(
                {n["pillar"] for n in linked}
                | set(p.get("subjects", []))
                | {
                    subject
                    for w in manifest.get("works", [])
                    if id in w.get("people", [])
                    for subject in w["subjects"]
                }
            ),
            "work_count": sum(
                id in w.get("people", []) for w in manifest.get("works", [])
            ),
            "profile_status": "source-linked research profile"
            if p.get("biography")
            else "recorded attribution; biographical research pending",
        }
        values["revision"] = p.get("revision", 1)
        if manifest.get("catalog_version", 1) >= 2:
            expected = digest({k: v for k, v in p.items() if k != "content_hash"})
            if p.get("content_hash") and p["content_hash"] != expected:
                raise ValueError("Contributor content hash mismatch")
            values["content_hash"] = expected
        else:
            values["content_hash"] = digest(values)
        result[id] = values
    return nodes, memberships, result, links
