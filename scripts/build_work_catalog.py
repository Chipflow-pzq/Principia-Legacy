"""Compile curated work/person metadata and evidence-pinned reading memberships.

Offline and deterministic. Edit config/representative_catalog.json to select
people and achievements; this compiler never mines author-list strings or
turns an award into a checked scientific claim. Frozen releases are untouched.
"""

import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from principia_legacy.catalog import contributor_id, name_key
from principia_legacy.common import (
    digest,
    read_json,
    read_lines,
    root_path,
)
from principia_legacy.records import visible
from principia_legacy.retrieval import normalize
from principia_legacy.storage import corpus, latest_records

ROOT = Path(__file__).resolve().parents[1]
# Explicit identity equivalences from the named institutional records. Never
# merge profiles just because they share a surname or research subject.
IDENTITIES = {
    "Sir Michael Francis Atiyah": "Michael Francis Atiyah",
    "John Milnor": "John Willard Milnor",
    "John F. Nash": "John F. Nash Jr.",
    "Maryna Viazovska": "Maryna S. Viazovska",
    "Grigori Perelman": "Grisha Perelman",
    "Sir Andrew J. Wiles": "Andrew Wiles",
    "Curtis T. Mcmullen": "Curtis T. McMullen",
    "Sir Antony Hoare": "Tony Hoare",
    "Sir Maurice V. Wilkes": "Maurice Wilkes",
    "Gordon Moore (In Memoriam)": "Gordon Moore",
}


def ref(r):
    return {k: r[k] for k in ("id", "revision", "content_hash")}


def compile_catalog(root, commit):
    records = corpus(root)
    current = latest_records(records)
    by_version = {(r["id"], r["revision"]): r for r in records}
    nodes = [r for r in current if r["type"] == "contribution" and visible(r)]
    sources = {r["id"]: r for r in current if r["type"] == "source"}
    topics = read_lines(root / "manifests/FRONTIER_REGISTRY.jsonl")
    topic_index = {normalize(t["title"]): t["id"] for t in topics}
    old_works = {w["id"]: w for w in read_json(root / "manifests/works.json", [])}
    old_people = {p["id"]: p for p in read_json(root / "manifests/people.json", [])}
    profiles = {p["id"]: p for p in read_json(root / "config/people_seeds.json", [])}
    for p in profiles.values():
        p.setdefault(
            "selection_reason",
            "Selected for a documented foundational idea or a major work already explained in the atlas. The profile sources identify the contribution and its scope.",
        )
    aliases = {
        name_key(n): p["id"]
        for p in profiles.values()
        for n in [p["name"], *p.get("aliases", [])]
    }
    works = {}
    work_by_title = {}
    for item in read_json(root / "config/representative_catalog.json", []):
        name = IDENTITIES.get(item["name"], item["name"])
        names = list(dict.fromkeys([name, item["name"], *item.get("aliases", [])]))
        matched = {aliases[name_key(n)] for n in names if name_key(n) in aliases}
        if len(matched) > 1:
            raise ValueError("Ambiguous explicit identity: " + name)
        pid = next(iter(matched), contributor_id(name))
        p = profiles.setdefault(
            pid,
            {
                "id": pid,
                "revision": 1,
                "name": name,
                "kind": "person",
                "aliases": [],
                "biography": item["biography"],
                "bio_sources": [],
                "subjects": [],
                "selection_reason": item["selection_reason"],
            },
        )
        for n in names:
            if n != p["name"] and n not in p["aliases"]:
                p["aliases"].append(n)
            key = name_key(n)
            if key in aliases and aliases[key] != pid:
                raise ValueError("Conflicting identity alias")
            aliases[key] = pid
        p["subjects"] = sorted(set(p.get("subjects", [])) | set(item["subjects"]))
        if item["provenance"] not in p["bio_sources"]:
            p["bio_sources"].append(item["provenance"])
        if not item.get("title"):
            continue
        title = item["title"]
        tid = item.get("topic_id") or topic_index.get(normalize(item["topic"]))
        if not tid:
            tid = "T-" + digest([item["subjects"][0], normalize(item["topic"])])[:12]
            topics.append(
                {
                    "id": tid,
                    "title": item["topic"],
                    "pillar": item["subjects"][0],
                    "tags": item["subjects"],
                    "area": "Selected discoveries and influential works",
                    "topic_kind": "research_catalog",
                    "flagship": False,
                    "endpoint": None,
                    "status": "unresolved",
                    "frontier_open": True,
                    "selection_reason": item["selection_reason"],
                    "source_passes": 0,
                    "checklist": [
                        {
                            "id": "move",
                            "requirement": "Extract the intellectual move from the underlying work",
                            "contributions": [],
                        },
                        {
                            "id": "scope",
                            "requirement": "Establish assumptions, limits and attribution",
                            "contributions": [],
                        },
                    ],
                    "gaps": [
                        "Catalog provenance is available; passage-grounded insight extraction and connection checking are pending."
                    ],
                    "search_outcomes": {
                        "attribution": "Institutional selection metadata only; primary-work attribution needs checking.",
                        "alternatives": "pending",
                        "limitations": "pending",
                    },
                    "backward_search": title,
                    "boundary_task": "Award recognition is selection provenance, not scientific evidence.",
                }
            )
            topic_index[normalize(item["topic"])] = tid
        # Equal named programs in the same recognition event form one work,
        # while distinct formulations or different award scopes stay separate.
        key = (normalize(title), item.get("recognition_year"), tuple(item["subjects"]))
        wid = work_by_title.setdefault(
            key, item.get("work_id") or "w-" + digest(key)[:16]
        )
        w = works.setdefault(
            wid,
            {
                "id": wid,
                "title": title,
                "kind": item["kind"],
                "subjects": item["subjects"],
                "summary": item["summary"],
                "people": [],
                "topic_ids": [],
                "provenance": [],
                "source_refs": [],
                "aliases": item.get("work_aliases", []),
                "representative": True,
                "selection_basis": item["selection_reason"],
            },
        )
        if item.get("recognition_year"):
            w["recognition_year"] = item["recognition_year"]
        if item.get("year"):
            w["year"] = item["year"]
        if pid not in w["people"]:
            w["people"].append(pid)
        if tid not in w["topic_ids"]:
            w["topic_ids"].append(tid)
        if item["provenance"] not in w["provenance"]:
            w["provenance"].append(item["provenance"])
        # Joint work summaries preserve each documented role, without granting
        # every contributor the same kind of originality credit.
        if item["summary"] not in w["summary"]:
            w["summary"] += " " + item["summary"]
        if item.get("source_id"):
            w.setdefault("evidence_source_ids", []).append(item["source_id"])
    # Explicit source bindings let a previously catalogue-only paper gain its
    # checked insights without creating a second, disconnected work identity.
    for w in read_json(root / "config/extra_works.json", []):
        if w["id"] in works:
            raise ValueError("Duplicate extra work")
        works[w["id"]] = w
    source_bindings = {}
    for w in works.values():
        for sid in w.get("evidence_source_ids", []):
            if sid in source_bindings and source_bindings[sid] != w["id"]:
                raise ValueError("Ambiguous explicit work/source binding: " + sid)
            source_bindings[sid] = w["id"]
    # Existing checked insights get explicit 'explains' memberships. A modern
    # textbook is not silently promoted into the original discovery.
    source_members = defaultdict(list)
    for n in nodes:
        for sid in {a["source_id"] for a in n["anchors"]}:
            source_members[sid].append(n)
    memberships = []
    shared = read_json(root / "manifests/topic_memberships.json", [])
    extra = defaultdict(set)
    node_refs = {n["id"]: ref(n) for n in nodes}
    for m in shared:
        if node_refs.get(m["contribution"]["id"]) == m["contribution"]:
            extra[m["contribution"]["id"]].add(m["topic_id"])
    for sid, ns in source_members.items():
        source = sources[sid]
        existing = works.get(source_bindings.get(sid))
        wid = existing["id"] if existing else "w-source-" + sid.removeprefix("s-")
        w = existing or {
            "id": wid,
            "title": source["title"],
            "kind": "exposition"
            if any(
                x in source["url"]
                for x in ["openstax.org", "textbooks.", "opendsa", "ostep"]
            )
            else "publication",
            "subjects": [],
            "summary": "A source work explaining the checked insights listed below. Consult the insight attribution notes to distinguish original discoveries from later exposition.",
            "people": sorted(
                {
                    aliases[name_key(n)]
                    for n in source["creators"]
                    if name_key(n) in aliases
                }
            ),
            "topic_ids": [],
            "provenance": [
                {
                    "url": source["url"],
                    "title": source["title"],
                    "note": "The pinned source editions contain the anchors used by the linked insights. This membership explains where an idea is discussed, not exclusive discovery credit.",
                }
            ],
            "source_refs": [],
            "aliases": [],
            "representative": False,
        }
        w["subjects"] = sorted(set(w["subjects"]) | {n["pillar"] for n in ns})
        w["topic_ids"] = sorted(
            set(w["topic_ids"])
            | {t for n in ns for t in set(n["dossiers"]) | extra[n["id"]]}
        )
        source_refs = {
            a["source_revision"]
            for n in ns
            for a in n["anchors"]
            if a["source_id"] == sid
        }
        w["source_refs"] = [ref(by_version[(sid, v)]) for v in sorted(source_refs)]
        w.pop("evidence_source_ids", None)
        if not w.get("year") and re.match(r"^\d{4}", source.get("date", "")):
            w["year"] = int(source["date"][:4])
        works[wid] = w
        for n in ns:
            memberships.append(
                {
                    "work_id": wid,
                    "contribution": ref(n),
                    "role": "explains",
                    "reason": "The source passages support this account of the insight; original authorship is assessed separately in its attribution.",
                    "anchors": [a for a in n["anchors"] if a["source_id"] == sid],
                }
            )
    topic_ids = {t for w in works.values() for t in w["topic_ids"]}
    topics = [
        t
        for t in topics
        if t.get("topic_kind") != "research_catalog" or t["id"] in topic_ids
    ]
    for person in profiles.values():
        old = old_people.get(person["id"])
        fields = {
            k: v for k, v in person.items() if k not in ("revision", "content_hash")
        }
        person["revision"] = old.get("revision", 1) if old else 1
        if old and fields != {
            k: v for k, v in old.items() if k not in ("revision", "content_hash")
        }:
            person["revision"] += 1
        person["content_hash"] = digest(
            {k: v for k, v in person.items() if k != "content_hash"}
        )
    for w in works.values():
        w.pop("evidence_source_ids", None)
        old = old_works.get(w["id"])
        w["revision"] = old["revision"] if old else 1
        if old and {
            k: v for k, v in old.items() if k not in ("revision", "content_hash")
        } != {k: v for k, v in w.items() if k != "revision"}:
            w["revision"] += 1
        w["content_hash"] = digest(w)
    for member in memberships:
        member["work"] = ref(works[member["work_id"]])
    # Curated cross-work use needs its own exact source-backed interpretation.
    # A metadata or claim revision never silently inherits this check.
    nodes_by_id = {n["id"]: n for n in nodes}
    for seed in read_json(root / "config/work_membership_seeds.json", []):
        w = works.get(seed["work_id"])
        n = nodes_by_id.get(seed["contribution"]["id"])
        if w and n and ref(w) == seed["work"] and ref(n) == seed["contribution"]:
            memberships.append(seed)
    commit.json(
        root / "manifests/works.json", sorted(works.values(), key=lambda w: w["id"])
    )
    commit.json(
        root / "manifests/work_insights.json",
        sorted(memberships, key=lambda m: (m["work_id"], m["contribution"]["id"])),
    )
    by_node = defaultdict(list)
    for member in memberships:
        if works[member["work_id"]]["kind"] != "exposition":
            by_node[member["contribution"]["id"]].append(member["work_id"])
    old_links = {
        r["id"]: r for r in read_json(root / "manifests/work_relations.json", [])
    }
    links = []
    for edge in current:
        if (
            edge["type"] != "relation"
            or not visible(edge)
            or len(edge["premises"]) != 1
        ):
            continue
        for left in by_node[edge["premises"][0]["id"]]:
            for right in by_node[edge["conclusion"]["id"]]:
                if left == right:
                    continue
                identity = "wr-" + digest([edge["id"], left, right])[:16]
                link = {
                    "id": identity,
                    "revision": 1,
                    "kind": "insight_projection",
                    "from": ref(works[left]),
                    "to": ref(works[right]),
                    "basis_relation": ref(edge),
                    "predicate": edge["predicate"],
                    "warrant": edge["warrant"],
                    "scope": "This connection concerns the linked insights within these works, not every claim or the entire history of either work.",
                    "provenance": [
                        {
                            "url": by_version[(a["source_id"], a["source_revision"])][
                                "url"
                            ],
                            "title": by_version[(a["source_id"], a["source_revision"])][
                                "title"
                            ],
                            "note": "Evidence anchor "
                            + a["anchor_id"]
                            + " at source revision "
                            + str(a["source_revision"]),
                        }
                        for a in edge["anchors"]
                    ],
                }
                old = old_links.get(identity)
                if old:
                    link["revision"] = old["revision"]
                    if {
                        k: v
                        for k, v in old.items()
                        if k not in ("revision", "content_hash")
                    } != {k: v for k, v in link.items() if k != "revision"}:
                        link["revision"] += 1
                link["content_hash"] = digest(link)
                links.append(link)
    commit.json(root / "manifests/work_relations.json", links)
    commit.json(
        root / "manifests/people.json",
        sorted(profiles.values(), key=lambda p: p["name"]),
    )
    commit.lines(root / "manifests/FRONTIER_REGISTRY.jsonl", topics)
    print(
        {
            "people": len(profiles),
            "works": len(works),
            "topics": len(topics),
            "work_insight_memberships": len(memberships),
        }
    )


if __name__ == "__main__":
    import argparse

    from principia_legacy.authoring_store import Commit, recover, writer

    parser = argparse.ArgumentParser()
    parser.add_argument("--data-home")
    args = parser.parse_args()
    root = root_path(args.data_home)
    with writer(root):
        recover(root)
        commit = Commit(root, "compile-work-catalog")
        compile_catalog(root, commit)
        commit.publish()
