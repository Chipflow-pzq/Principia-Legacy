"""Deterministic compilation into a read-only, snapshot-aware SQLite atlas."""

import json
import os
import sqlite3
import tempfile
from pathlib import Path

from . import exploration_index, query_index, retrieval
from .catalog import navigation_index
from .common import digest, encode_snapshot, internal_snapshot, read_json, read_lines
from .records import validate, visible
from .works import compile_works


def corpus(root):
    return [
        r
        for p in sorted((Path(root) / "corpus").rglob("*.jsonl"))
        for r in read_lines(p)
    ]


def latest_records(records):
    latest = {}
    for r in records:
        if r["id"] not in latest or r["revision"] > latest[r["id"]]["revision"]:
            latest[r["id"]] = r
    return sorted(latest.values(), key=lambda x: x["id"])


def manifest(root, release_id="working", records=None):
    root = Path(root)
    records = latest_records(corpus(root) if records is None else records)
    return {
        "release_id": release_id,
        "schema_version": 1,
        "record_refs": [
            {
                "id": r["id"],
                "revision": r["revision"],
                "content_hash": r["content_hash"],
            }
            for r in records
        ],
        "dossiers": read_lines(root / "manifests/FRONTIER_REGISTRY.jsonl"),
        "tours": read_json(root / "tours/tours.json", []),
        "idea_families": read_json(root / "manifests/idea_families.json", []),
        "route_assessments": read_json(root / "manifests/route_assessments.json", []),
        "topic_memberships": read_json(root / "manifests/topic_memberships.json", []),
        "people": read_json(root / "manifests/people.json", []),
        "credit_groups": read_json(root / "manifests/credit_groups.json", []),
        "coverage_targets": read_json(root / "config/coverage_targets.json", {}),
        **(
            {
                "catalog_version": 2,
                "works": read_json(root / "manifests/works.json", []),
                "work_insights": read_json(root / "manifests/work_insights.json", []),
                "work_relations": read_json(root / "manifests/work_relations.json", []),
                "search_concepts": read_json(root / "config/search_concepts.json", []),
            }
            if (root / "manifests/works.json").exists()
            else {}
        ),
        "maturity": "exploratory",
        "human_review_claim": "Only explicit human review records count. No expert audit is implied.",
    }


def build(root, release_id=None):
    from .authoring_store import recover, writer

    root = Path(root)
    # Compilers serialize separately. Capture a consistent canonical generation
    # briefly under the authoring lock; expensive indexing cannot block receipts
    # or admission. A later admission is picked up by the next queued build.
    lock_path = root / ".work/compilation.sqlite"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock = sqlite3.connect(lock_path, timeout=600)
    try:
        lock.execute("BEGIN IMMEDIATE")
        with writer(root):
            recover(root)
            records = corpus(root)
            retained = set(read_json(root / "config/reader_history.json", []))
            saved = [
                read_json(p)
                for p in sorted((root / "manifests/releases").glob("*.json"))
                if not internal_snapshot(p.stem)
                or p.stem == release_id
                or p.stem in retained
            ]
            working = (
                manifest(root, records=records)
                if not release_id or release_id == "working"
                else None
            )
        return _build(root, release_id, records, saved, working)
    finally:
        lock.rollback()
        lock.close()


def _build(root, release_id=None, records=None, saved=None, working=None):
    root = Path(root)
    retained = set(read_json(root / "config/reader_history.json", []))
    records = corpus(root) if records is None else records
    errors = validate(records)
    if errors:
        raise ValueError("\n".join(errors[:30]))
    saved = (
        [
            read_json(p)
            for p in sorted((root / "manifests/releases").glob("*.json"))
            if not internal_snapshot(p.stem)
            or p.stem == release_id
            or p.stem in retained
        ]
        if saved is None
        else saved
    )
    # Internal correction checkpoints remain reproducible manifests. Index them
    # only on explicit restoration, avoiding one full search index per recheck.
    saved = [
        m
        for m in saved
        if not internal_snapshot(m["release_id"])
        or m["release_id"] == release_id
        or m["release_id"] in retained
    ]
    if release_id and release_id != "working":
        if not any(m["release_id"] == release_id for m in saved):
            raise ValueError("Unknown frozen release")
        current = release_id
    else:
        saved = [*saved, working if working is not None else manifest(root)]
        current = "working"
    dest = root / "build/atlas.sqlite"
    dest.parent.mkdir(exist_ok=True)
    # A unique temporary file also protects a rolling authoring-code upgrade
    # from an older compiler that still uses the legacy fixed temp filename.
    descriptor, temporary = tempfile.mkstemp(
        prefix="atlas-", suffix=".tmp.sqlite", dir=dest.parent
    )
    os.close(descriptor)
    temp = Path(temporary)
    db = sqlite3.connect(temp)
    try:
        db.executescript("""
        PRAGMA page_size=4096;
        CREATE TABLE records(id TEXT NOT NULL, revision INTEGER NOT NULL, type TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(id,revision));
        CREATE TABLE snapshots(id TEXT PRIMARY KEY,payload TEXT NOT NULL);
        CREATE TABLE members(snapshot TEXT NOT NULL,id TEXT NOT NULL,revision INTEGER NOT NULL,PRIMARY KEY(snapshot,id));
        CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT);
        CREATE VIRTUAL TABLE search USING fts5(revision UNINDEXED,id UNINDEXED,title,claim,explanation, tokenize='unicode61 remove_diacritics 2');
        CREATE INDEX record_types ON records(type);
        CREATE INDEX reviews_target ON records(json_extract(payload,'$.target.content_hash')) WHERE type='review';
        CREATE TABLE adjacency(snapshot TEXT NOT NULL, relation_id TEXT NOT NULL, endpoint_id TEXT NOT NULL, role TEXT NOT NULL, layer TEXT NOT NULL);
        CREATE INDEX adjacency_endpoint ON adjacency(snapshot,endpoint_id,layer);
        CREATE INDEX adjacency_relation ON adjacency(snapshot,relation_id);
        CREATE TABLE topic_members(snapshot TEXT,topic TEXT,id TEXT,revision INTEGER,origin TEXT,reason TEXT,PRIMARY KEY(snapshot,topic,id));
        CREATE INDEX topic_by_node ON topic_members(snapshot,id);
        CREATE TABLE people(snapshot TEXT,id TEXT,payload TEXT,PRIMARY KEY(snapshot,id));
        CREATE TABLE person_members(snapshot TEXT,person TEXT,id TEXT,revision INTEGER,credit TEXT,PRIMARY KEY(snapshot,person,id));
        CREATE INDEX person_by_node ON person_members(snapshot,id);
        CREATE TABLE works(snapshot TEXT,id TEXT,payload TEXT,PRIMARY KEY(snapshot,id));
        CREATE TABLE work_links(snapshot TEXT,id TEXT,payload TEXT,PRIMARY KEY(snapshot,id));
        CREATE TABLE work_members(snapshot TEXT,work TEXT,id TEXT,payload TEXT,PRIMARY KEY(snapshot,work,id));
        CREATE INDEX work_by_node ON work_members(snapshot,id);
        CREATE TABLE work_topics(snapshot TEXT,work TEXT,topic TEXT,PRIMARY KEY(snapshot,topic,work));
        CREATE TABLE work_people(snapshot TEXT,work TEXT,person TEXT,PRIMARY KEY(snapshot,person,work));
        CREATE VIRTUAL TABLE catalog_search USING fts5(snapshot UNINDEXED,id UNINDEXED,kind UNINDEXED,title,description,tokenize='unicode61 remove_diacritics 2');
        """)
        retrieval.install(db)
        query_index.install(db)
        exploration_index.install(db)
        indexed = {(r["id"], r["revision"]): r for r in records}
        for r in sorted(records, key=lambda x: (x["id"], x["revision"])):
            db.execute(
                "INSERT INTO records VALUES(?,?,?,?)",
                (
                    r["id"],
                    r["revision"],
                    r["type"],
                    json.dumps(r, sort_keys=True, ensure_ascii=False),
                ),
            )
            if r["type"] == "contribution" and visible(r):
                db.execute(
                    "INSERT INTO search VALUES(?,?,?,?,?)",
                    (
                        r["revision"],
                        r["id"],
                        r["title"],
                        r["claim"],
                        "\n".join(
                            [
                                r["explanation"],
                                r["problem"],
                                r["conceptual_move"],
                                *r["assumptions"],
                                *r["limits"],
                                *(a["name"] for a in r["attribution"]),
                                *r.get("tags", []),
                            ]
                        ),
                    ),
                )
        for m in saved:
            membership = {ref["id"]: ref["revision"] for ref in m["record_refs"]}
            for ref in m["record_refs"]:
                record = indexed.get((ref["id"], ref["revision"]))
                if (
                    record
                    and record["type"] == "relation"
                    and visible(record)
                    and any(
                        membership.get(endpoint["id"]) != endpoint["revision"]
                        for endpoint in [*record["premises"], record["conclusion"]]
                    )
                ):
                    raise ValueError(
                        "Visible relation does not pin the active endpoint revision in snapshot "
                        + m["release_id"]
                    )
            db.execute(
                "INSERT INTO snapshots VALUES(?,?)",
                (m["release_id"], encode_snapshot(m)),
            )
            snapshot_records = [
                indexed[(r["id"], r["revision"])] for r in m["record_refs"]
            ]
            nodes, topic_links, people, credits = navigation_index(
                m, snapshot_records, records
            )
            works, work_members, work_links = compile_works(m, nodes, records)
            query_index.populate(db, m, snapshot_records, people, works)
            # The compiled snapshot stores only revision-valid interpretations.
            # Its immutable manifest remains the reproducible source of truth.
            db.executemany(
                "INSERT INTO work_links VALUES(?,?,?)",
                (
                    (
                        m["release_id"],
                        r["id"],
                        json.dumps(r, ensure_ascii=False, sort_keys=True),
                    )
                    for r in work_links
                ),
            )
            for id, work in works.items():
                db.execute(
                    "INSERT INTO works VALUES(?,?,?)",
                    (
                        m["release_id"],
                        id,
                        json.dumps(work, ensure_ascii=False, sort_keys=True),
                    ),
                )
                db.execute(
                    "INSERT INTO catalog_search VALUES(?,?,?,?,?)",
                    (
                        m["release_id"],
                        id,
                        "work",
                        work["title"],
                        " ".join(
                            [
                                work.get("summary", ""),
                                *work.get("aliases", []),
                                *(
                                    people[p]["name"]
                                    for p in work.get("people", [])
                                    if p in people
                                ),
                            ]
                        ),
                    ),
                )
                db.executemany(
                    "INSERT INTO work_topics VALUES(?,?,?)",
                    ((m["release_id"], id, t) for t in work["topic_ids"]),
                )
                db.executemany(
                    "INSERT INTO work_people VALUES(?,?,?)",
                    ((m["release_id"], id, p) for p in work.get("people", [])),
                )
            for (work, id), member in work_members.items():
                db.execute(
                    "INSERT INTO work_members VALUES(?,?,?,?)",
                    (m["release_id"], work, id, json.dumps(member, sort_keys=True)),
                )
            for (topic, node), value in sorted(topic_links.items()):
                db.execute(
                    "INSERT INTO topic_members VALUES(?,?,?,?,?,?)",
                    (
                        m["release_id"],
                        topic,
                        node,
                        nodes[node]["revision"],
                        value["origin"],
                        value["reason"],
                    ),
                )
            for id, person in sorted(people.items()):
                db.execute(
                    "INSERT INTO people VALUES(?,?,?)",
                    (
                        m["release_id"],
                        id,
                        json.dumps(person, sort_keys=True, ensure_ascii=False),
                    ),
                )
                db.execute(
                    "INSERT INTO catalog_search VALUES(?,?,?,?,?)",
                    (
                        m["release_id"],
                        id,
                        "person",
                        person["name"],
                        " ".join(
                            [*person.get("aliases", []), person.get("biography", "")]
                        ),
                    ),
                )
            for (person, node), credit in sorted(credits.items()):
                if person in people:
                    db.execute(
                        "INSERT INTO person_members VALUES(?,?,?,?,?)",
                        (
                            m["release_id"],
                            person,
                            node,
                            nodes[node]["revision"],
                            json.dumps(credit, sort_keys=True),
                        ),
                    )
            for topic in m["dossiers"]:
                db.execute(
                    "INSERT INTO catalog_search VALUES(?,?,?,?,?)",
                    (
                        m["release_id"],
                        topic["id"],
                        "topic",
                        topic["title"],
                        " ".join(
                            [
                                topic.get("backward_search", ""),
                                *topic.get("aliases", []),
                            ]
                        ),
                    ),
                )
            for ref in m["record_refs"]:
                r = indexed.get((ref["id"], ref["revision"]))
                if not r or r["content_hash"] != ref["content_hash"]:
                    raise ValueError("Snapshot references missing or modified record")
                db.execute(
                    "INSERT INTO members VALUES(?,?,?)",
                    (m["release_id"], r["id"], r["revision"]),
                )
                if r["type"] == "relation" and visible(r):
                    db.executemany(
                        "INSERT INTO adjacency VALUES(?,?,?,?,?)",
                        [
                            (m["release_id"], r["id"], endpoint["id"], role, r["layer"])
                            for role, endpoints in (
                                ("premise", r["premises"]),
                                ("conclusion", [r["conclusion"]]),
                            )
                            for endpoint in endpoints
                        ],
                    )
            retrieval.index(
                db,
                m["release_id"],
                [
                    *(n["title"] for n in nodes.values()),
                    *(d["title"] for d in m["dossiers"]),
                    *(
                        label
                        for p in people.values()
                        for label in [p["name"], *p.get("aliases", [])]
                    ),
                    *(
                        label
                        for w in works.values()
                        for label in [w["title"], *w.get("aliases", [])]
                    ),
                    *(
                        term
                        for concept in m.get("search_concepts", [])
                        for term in concept["terms"]
                    ),
                ],
            )
        db.execute("INSERT INTO metadata VALUES(?,?)", ("current_release", current))
        from .storage import Atlas

        for m in saved:
            reader = object.__new__(Atlas)
            reader.root, reader.db, reader.release = root, db, m["release_id"]
            reader.manifest, reader.snapshot_hash = m, digest(m)
            reader._human_states = None
            reader.context = m
            query_index.summarize(db, m, reader._legacy_dossiers()["dossiers"])
            query_index.rank_topics(db, m)
            exploration_index.compile_shards(db, m["release_id"])
            compact = {
                k: m.get(k, []) for k in ("tours", "idea_families", "search_concepts")
            }
            compact["coverage_targets"] = m.get("coverage_targets", {})
            db.execute(
                "INSERT INTO snapshot_context VALUES(?,?,?,?)",
                (
                    m["release_id"],
                    digest(m),
                    json.dumps(compact, ensure_ascii=False),
                    json.dumps(reader._calculate_info(), ensure_ascii=False),
                ),
            )
        db.commit()
        db.execute("ANALYZE")
        db.execute("VACUUM")
        db.close()
        # mkstemp uses 0600. Authoring and the read-only service may use different
        # accounts, so the published reader index needs read permission. Private
        # source archives and credentials are not part of this artifact.
        temp.chmod(0o644)
        temp.replace(dest)
    except Exception:
        db.close()
        temp.unlink(missing_ok=True)
        raise
    return {
        "database": str(dest),
        "bytes": dest.stat().st_size,
        "release_id": current,
        "records": len(records),
    }
