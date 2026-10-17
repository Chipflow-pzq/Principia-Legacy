"""Deterministic compilation into a read-only, snapshot-aware SQLite atlas."""

import json
import sqlite3
from collections import OrderedDict
from hashlib import sha256
from pathlib import Path
from threading import Lock

from . import retrieval
from .catalog import navigation_index
from .common import digest, read_json, read_lines
from .records import PILLARS, PREDICATES, validate, visible
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


def manifest(root, release_id="working"):
    root = Path(root)
    records = latest_records(corpus(root))
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
    root = Path(root)
    records = corpus(root)
    errors = validate(records)
    if errors:
        raise ValueError("\n".join(errors[:30]))
    saved = [read_json(p) for p in sorted((root / "manifests/releases").glob("*.json"))]
    # Internal correction checkpoints remain reproducible manifests. Index them
    # only on explicit restoration, avoiding one full search index per recheck.
    saved = [
        m
        for m in saved
        if not m["release_id"].startswith("before-") or m["release_id"] == release_id
    ]
    if release_id and release_id != "working":
        if not any(m["release_id"] == release_id for m in saved):
            raise ValueError("Unknown frozen release")
        current = release_id
    else:
        saved = [*saved, manifest(root)]
        current = "working"
    dest = root / "build/atlas.sqlite"
    dest.parent.mkdir(exist_ok=True)
    temp = dest.with_suffix(".tmp.sqlite")
    temp.unlink(missing_ok=True)
    db = sqlite3.connect(temp)
    try:
        db.executescript("""
        PRAGMA page_size=4096;
        CREATE TABLE records(id TEXT NOT NULL, revision INTEGER NOT NULL, type TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(id,revision));
        CREATE TABLE snapshots(id TEXT PRIMARY KEY,payload TEXT NOT NULL);
        CREATE TABLE members(snapshot TEXT NOT NULL,id TEXT NOT NULL,revision INTEGER NOT NULL,PRIMARY KEY(snapshot,id));
        CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT);
        CREATE VIRTUAL TABLE search USING fts5(snapshot UNINDEXED,id UNINDEXED,title,claim,explanation, tokenize='unicode61 remove_diacritics 2');
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
                (m["release_id"], json.dumps(m, sort_keys=True, ensure_ascii=False)),
            )
            snapshot_records = [
                indexed[(r["id"], r["revision"])] for r in m["record_refs"]
            ]
            nodes, topic_links, people, credits = navigation_index(
                m, snapshot_records, records
            )
            works, work_members, work_links = compile_works(m, nodes, records)
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
                if r["type"] == "contribution" and visible(r):
                    db.execute(
                        "INSERT INTO search VALUES(?,?,?,?,?)",
                        (
                            m["release_id"],
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
                elif r["type"] == "relation" and visible(r):
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
        db.commit()
        db.execute("VACUUM")
        db.close()
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


_snapshots = OrderedDict()
_snapshot_lock = Lock()


def _snapshot(payload):
    """Cache two public snapshots without retaining multi-megabyte JSON keys.

    Exact payload hashes invalidate working builds. Two entries cover a release
    comparison; source strings and personal queries are never retained as keys.
    The lock prevents parallel first-page requests from decoding duplicate copies.
    """
    key = sha256(payload.encode("utf-8")).digest()
    with _snapshot_lock:
        if key in _snapshots:
            _snapshots.move_to_end(key)
        else:
            value = json.loads(payload)
            _snapshots[key] = (value, digest(value))
            while len(_snapshots) > 2:
                _snapshots.popitem(last=False)
        return _snapshots[key]


class Atlas:
    def __init__(self, root, release=None):
        self.root = Path(root)
        path = self.root / "build/atlas.sqlite"
        if not path.exists():
            raise ValueError("Atlas database missing. Run build --offline first.")
        self.db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
        self.db.execute("PRAGMA query_only=ON")
        self.release = (
            release
            or self.db.execute(
                "SELECT value FROM metadata WHERE key='current_release'"
            ).fetchone()[0]
        )
        try:
            row = self.db.execute(
                "SELECT payload FROM snapshots WHERE id=?", (self.release,)
            ).fetchone()
            if not row:
                raise ValueError("Unknown release snapshot")
            self.manifest, self.snapshot_hash = _snapshot(row[0])
        except Exception:
            self.db.close()
            raise
        self._records = None
        self._human_states = None
        self._extra_memberships = {
            (m["topic_id"], m["contribution"]["id"]): m
            for m in self.manifest.get("topic_memberships", [])
        }

    def close(self):
        self.db.close()

    @property
    def records(self):
        if self._records is None:
            self._records = [
                json.loads(r[0])
                for r in self.db.execute(
                    "SELECT r.payload FROM records r JOIN members m ON r.id=m.id AND r.revision=m.revision WHERE m.snapshot=? ORDER BY r.id",
                    (self.release,),
                )
            ]
        return self._records

    def human_state(self, record):
        if self._human_states is None:
            self._human_states = {}
            rows = self.db.execute(
                "SELECT r.payload FROM records r JOIN members m ON r.id=m.id AND r.revision=m.revision "
                "WHERE m.snapshot=? AND r.type='review' AND json_extract(r.payload,'$.reviewer_type')='human'",
                (self.release,),
            )
            for row in rows:
                review = json.loads(row[0])
                key = review["target"]["content_hash"]
                if review["judgment"] in ("disputed", "rejected"):
                    self._human_states[key] = "disputed"
                elif (
                    review["judgment"] == "accepted"
                    and self._human_states.get(key) != "disputed"
                ):
                    previous = self._human_states.get(key)
                    self._human_states[key] = (
                        "domain_expert"
                        if previous == "domain_expert"
                        or review["scope"] == "domain_expert"
                        else "editorial"
                    )
        return self._human_states.get(record["content_hash"], "not_reviewed")

    def response(self, **values):
        return {
            "release_id": self.release,
            "snapshot_hash": self.snapshot_hash,
            **values,
        }

    def contributions(self):
        return [
            json.loads(row[0])
            for row in self.db.execute(
                "SELECT r.payload FROM records r JOIN members m ON r.id=m.id AND r.revision=m.revision WHERE m.snapshot=? AND r.type='contribution' ORDER BY r.id",
                (self.release,),
            )
        ]

    def exploration_index(self, offset=0, limit=200):
        """Public snapshot pages for browser-local matching; no personal query."""
        offset, limit = int(offset), int(limit)
        if not 0 <= offset <= 10000 or not 1 <= limit <= 200:
            raise ValueError("Invalid exploration index page")
        where = (
            "FROM records r JOIN members m ON r.id=m.id AND r.revision=m.revision "
            "WHERE m.snapshot=? AND r.type='contribution' "
            "AND json_extract(r.payload,'$.publication_state') IN ('exploratory','reviewed') "
            "AND json_extract(r.payload,'$.machine_screening')='passed'"
        )
        total = self.db.execute("SELECT COUNT(*) " + where, (self.release,)).fetchone()[
            0
        ]
        fields = (
            "id",
            "revision",
            "content_hash",
            "title",
            "kind",
            "pillar",
            "claim",
            "explanation",
            "assumptions",
            "limits",
            "attribution",
            "date",
        )
        entries = []
        for row in self.db.execute(
            "SELECT r.payload " + where + " ORDER BY r.id LIMIT ? OFFSET ?",
            (self.release, limit, offset),
        ):
            record = json.loads(row[0])
            entries.append({key: record[key] for key in fields})
        # Ship public adjacency with the same query-free pages. The browser can
        # follow a matched foundation without revealing the user's selected seeds.
        by_id = {entry["id"]: entry for entry in entries}
        neighbors = {id: set() for id in by_id}
        for relation in self.adjacent_relations(
            set(by_id), {p[0] for p in PREDICATES.values()}
        ):
            if not relation or not visible(relation):
                continue
            refs = [*relation["premises"], relation["conclusion"]]
            try:
                endpoints = [self.get(ref["id"], "contribution") for ref in refs]
            except KeyError:
                continue
            if any(
                not n or not visible(n) or n["revision"] != ref["revision"]
                for n, ref in zip(endpoints, refs)
            ):
                continue
            ids = {ref["id"] for ref in refs}
            for id in ids & by_id.keys():
                neighbors[id].update(ids - {id})
        for id, entry in by_id.items():
            entry["neighbors"] = sorted(neighbors[id])
        return self.response(entries=entries, total=total, offset=offset, limit=limit)

    def adjacent_relations(self, ids, layers):
        if not ids or not layers:
            return []
        placeholders = ",".join("?" for _ in ids)
        layer_placeholders = ",".join("?" for _ in layers)
        query = f"SELECT DISTINCT relation_id FROM adjacency WHERE snapshot=? AND endpoint_id IN ({placeholders}) AND layer IN ({layer_placeholders}) ORDER BY relation_id"
        return [
            self.get(row[0], "relation")
            for row in self.db.execute(
                query, (self.release, *sorted(ids), *sorted(layers))
            )
        ]

    def get(self, id, kind=None):
        row = self.db.execute(
            "SELECT r.payload FROM records r JOIN members m ON r.id=m.id AND r.revision=m.revision WHERE m.snapshot=? AND r.id=?",
            (self.release, id),
        ).fetchone()
        if not row:
            raise KeyError(id)
        r = json.loads(row[0])
        if kind and r["type"] != kind:
            raise KeyError(id)
        if r["type"] in ("contribution", "relation") and not visible(r):
            raise KeyError(id)
        return r

    def inspect(self, id, kind):
        r = self.get(id, kind)
        topics = self.topics_for(id) if kind == "contribution" else []
        navigation_anchors = [a for t in topics for a in t.get("anchors", [])]
        sources = {}
        for anchor in [*r.get("anchors", []), *navigation_anchors]:
            row = self.db.execute(
                "SELECT payload FROM records WHERE id=? AND revision=?",
                (anchor["source_id"], anchor["source_revision"]),
            ).fetchone()
            if row:
                sources[(anchor["source_id"], anchor["source_revision"])] = json.loads(
                    row[0]
                )
        reviews = [
            json.loads(row[0])
            for row in self.db.execute(
                "SELECT r.payload FROM records r JOIN members m ON r.id=m.id AND r.revision=m.revision "
                "WHERE m.snapshot=? AND r.type='review' AND json_extract(r.payload,'$.target.content_hash')=?",
                (self.release, r["content_hash"]),
            )
        ]
        return self.response(
            record={**r, "effective_human_review": self.human_state(r)},
            works=self.works_for(id) if kind == "contribution" else [],
            sources=list(sources.values()),
            topics=topics,
            navigation_source_anchors=navigation_anchors,
            people=[
                json.loads(row[0])
                for row in self.db.execute(
                    "SELECT p.payload FROM people p JOIN person_members m ON p.snapshot=m.snapshot AND p.id=m.person WHERE m.snapshot=? AND m.id=? ORDER BY json_extract(p.payload,'$.name')",
                    (self.release, id),
                )
            ]
            if kind == "contribution"
            else [],
            reviews=reviews,
            idea_families=[
                {
                    **f,
                    "members": [
                        {k: n[k] for k in ("id", "revision", "title")}
                        for n in self.contributions()
                        if n["id"] in f["contributions"] and visible(n)
                    ],
                }
                for f in self.manifest.get("idea_families", [])
                if id in f["contributions"]
            ],
            endpoints=[
                {k: self.get(ref["id"])[k] for k in ("id", "revision", "title")}
                for ref in [*r["premises"], r["conclusion"]]
            ]
            if kind == "relation"
            else [],
        )

    def topics_for(self, id):
        memberships = {
            row[0]: {
                "reason": row[1],
                "origin": row[2],
                **{
                    k: v
                    for k, v in self._extra_memberships.get((row[0], id), {}).items()
                    if k in {"anchors", "screening_request_id", "source_url"}
                    and row[2] != "record"
                },
            }
            for row in self.db.execute(
                "SELECT topic,reason,origin FROM topic_members WHERE snapshot=? AND id=?",
                (self.release, id),
            )
        }
        return [
            {**{k: d[k] for k in ("id", "title", "pillar")}, **memberships[d["id"]]}
            for d in self.manifest["dossiers"]
            if d["id"] in memberships
        ]

    def person(self, id, human=False):
        row = self.db.execute(
            "SELECT payload FROM people WHERE snapshot=? AND id=?", (self.release, id)
        ).fetchone()
        if not row:
            raise KeyError(id)
        person = json.loads(row[0])
        contributions = []
        for node, credit in self.db.execute(
            "SELECT id,credit FROM person_members WHERE snapshot=? AND person=?",
            (self.release, id),
        ):
            record = self.get(node, "contribution")
            if not human or self.human_state(record) != "not_reviewed":
                contributions.append({**record, "credit": json.loads(credit)})
        contributions.sort(
            key=lambda n: (
                n["date"]["year"] is None,
                n["date"]["year"] or 0,
                n["title"],
            )
        )
        topic_ids = {t["id"] for n in contributions for t in self.topics_for(n["id"])}
        works = self.works(person=id, human=human, limit=100)["works"]
        topic_ids.update(t for w in works for t in w["topic_ids"])
        return self.response(
            person=person,
            contributions=contributions,
            works=works,
            topics=[
                {k: d[k] for k in ("id", "title", "pillar")}
                for d in self.manifest["dossiers"]
                if d["id"] in topic_ids
            ],
            notice="Recorded credit and navigational topic membership do not establish exclusive authorship, priority, or influence. Biographical sources are identified separately.",
        )

    def people(self, query="", limit=60, offset=0, human=False, pillar=None):
        limit = min(max(int(limit), 1), 100)
        offset = max(int(offset), 0)
        if len(query) > 500:
            raise ValueError("Search query is too long")
        matches = self.catalog_matches(query, "person") if query.strip() else None
        rows = [
            json.loads(r[0])
            for r in self.db.execute(
                "SELECT payload FROM people WHERE snapshot=? ORDER BY json_extract(payload,'$.name') COLLATE NOCASE",
                (self.release,),
            )
        ]
        if matches is not None:
            rows = [r for r in rows if r["id"] in matches]
            rank = {id: i for i, id in enumerate(matches)}
            rows.sort(key=lambda r: rank[r["id"]])
        if pillar:
            rows = [r for r in rows if pillar in r["subjects"]]
        if human:
            reviewed = {
                id
                for id, content_hash in self.db.execute(
                    "SELECT r.id,json_extract(r.payload,'$.content_hash') FROM records r JOIN members m ON r.id=m.id AND r.revision=m.revision WHERE m.snapshot=? AND r.type='contribution'",
                    (self.release,),
                )
                if self.human_state({"content_hash": content_hash}) != "not_reviewed"
            }
            linked = {
                person
                for person, node in self.db.execute(
                    "SELECT person,id FROM person_members WHERE snapshot=?",
                    (self.release,),
                )
                if node in reviewed
            }
            rows = [r for r in rows if r["id"] in linked]
        return self.response(
            people=rows[offset : offset + limit], total=len(rows), offset=offset
        )

    def search_plan(self, query):
        if len(query) > 500:
            raise ValueError("Search query is too long")
        return retrieval.plan(
            self.db, self.release, query, self.manifest.get("search_concepts", [])
        )

    def catalog_matches(self, query, kind, queries=None):
        queries = queries if queries is not None else self.search_plan(query)["queries"]
        expression = retrieval.expression(queries)
        if not expression:
            return []
        return [
            r[0]
            for r in self.db.execute(
                "SELECT id FROM catalog_search WHERE catalog_search MATCH ? AND snapshot=? AND kind=? ORDER BY CASE WHEN lower(title)=lower(?) THEN 0 WHEN instr(lower(title),lower(?))=1 THEN 1 ELSE 2 END,bm25(catalog_search,0,0,0,8,1),id",
                (expression, self.release, kind, query.strip(), query.strip()),
            )
        ]

    def works_for(self, node):
        return [
            json.loads(r[0])
            for r in self.db.execute(
                "SELECT w.payload FROM works w JOIN work_members m ON w.snapshot=m.snapshot AND w.id=m.work WHERE m.snapshot=? AND m.id=? ORDER BY w.id",
                (self.release, node),
            )
        ]

    def works(
        self,
        query="",
        pillar=None,
        topic=None,
        person=None,
        human=False,
        limit=40,
        offset=0,
    ):
        limit = min(max(int(limit), 1), 100)
        offset = max(0, int(offset))
        if len(query) > 500:
            raise ValueError("Search query is too long")
        ids = self.catalog_matches(query, "work") if query.strip() else None
        where = ["w.snapshot=?"]
        params = [self.release]
        for value, table, column in (
            (topic, "work_topics", "topic"),
            (person, "work_people", "person"),
        ):
            if value:
                where.append(
                    f"EXISTS(SELECT 1 FROM {table} l WHERE l.snapshot=w.snapshot AND l.work=w.id AND l.{column}=?)"
                )
                params.append(value)
        if pillar:
            where.append(
                "EXISTS(SELECT 1 FROM json_each(w.payload,'$.subjects') WHERE value=?)"
            )
            params.append(pillar)
        rows = [
            json.loads(r[0])
            for r in self.db.execute(
                "SELECT w.payload FROM works w WHERE "
                + " AND ".join(where)
                + " ORDER BY json_extract(w.payload,'$.title') COLLATE NOCASE",
                params,
            )
        ]
        if ids is not None:
            ranks = {id: i for i, id in enumerate(ids)}
            rows = sorted(
                (w for w in rows if w["id"] in ranks), key=lambda w: ranks[w["id"]]
            )
        if human:
            accepted = {
                work
                for work, content_hash in self.db.execute(
                    "SELECT m.work,json_extract(r.payload,'$.content_hash') FROM work_members m JOIN members a ON a.snapshot=m.snapshot AND a.id=m.id JOIN records r ON r.id=a.id AND r.revision=a.revision WHERE m.snapshot=?",
                    (self.release,),
                )
                if self.human_state({"content_hash": content_hash}) != "not_reviewed"
            }
            rows = [w for w in rows if w["id"] in accepted]
        return self.response(
            works=rows[offset : offset + limit],
            total=len(rows),
            limit=limit,
            offset=offset,
        )

    def work(self, id, human=False):
        row = self.db.execute(
            "SELECT payload FROM works WHERE snapshot=? AND id=?", (self.release, id)
        ).fetchone()
        if not row:
            raise KeyError(id)
        work = json.loads(row[0])
        contributions = []
        memberships = []
        for node, payload in self.db.execute(
            "SELECT id,payload FROM work_members WHERE snapshot=? AND work=?",
            (self.release, id),
        ):
            n = self.get(node, "contribution")
            if not human or self.human_state(n) != "not_reviewed":
                contributions.append(n)
                memberships.append(json.loads(payload))
        related = []
        for link in (
            json.loads(r[0])
            for r in self.db.execute(
                "SELECT payload FROM work_links WHERE snapshot=?", (self.release,)
            )
        ):
            if id not in (link["from"]["id"], link["to"]["id"]):
                continue
            basis = self.get(link["basis_relation"]["id"], "relation")
            if human and (
                self.human_state(basis) == "not_reviewed"
                or any(
                    self.human_state(self.get(e["id"], "contribution"))
                    == "not_reviewed"
                    for e in [*basis["premises"], basis["conclusion"]]
                )
            ):
                continue
            ends = [
                self.db.execute(
                    "SELECT payload FROM works WHERE snapshot=? AND id=?",
                    (self.release, e["id"]),
                ).fetchone()
                for e in (link["from"], link["to"])
            ]
            if all(
                row
                and all(
                    json.loads(row[0])[k] == ref[k]
                    for k in ("revision", "content_hash")
                )
                for row, ref in zip(ends, (link["from"], link["to"]))
            ):
                related.append(
                    {
                        **link,
                        "layer": PREDICATES[link["predicate"]][0],
                        "symmetric": PREDICATES[link["predicate"]][1],
                        "machine_screening": basis["machine_screening"],
                        "human_review": self.human_state(basis),
                        "endpoints": [json.loads(r[0]) for r in ends],
                    }
                )
        eligible_ids = [n["id"] for n in contributions]
        shared_filter = (
            " AND a.id IN (" + ",".join("?" for _ in eligible_ids) + ")"
            if human
            else ""
        )
        shared = (
            [
                {"work": json.loads(row[0]), "insight_count": row[1]}
                for row in self.db.execute(
                    "SELECT w.payload,COUNT(*) FROM work_members a JOIN work_members b ON a.snapshot=b.snapshot AND a.id=b.id AND a.work!=b.work JOIN works w ON w.snapshot=b.snapshot AND w.id=b.work WHERE a.snapshot=? AND a.work=?"
                    + shared_filter
                    + " GROUP BY w.id ORDER BY COUNT(*) DESC,w.id LIMIT 12",
                    (self.release, id, *(eligible_ids if human else [])),
                )
            ]
            if not human or eligible_ids
            else []
        )
        source_versions = []
        for ref in work.get("source_refs", []):
            row = self.db.execute(
                "SELECT payload FROM records WHERE id=? AND revision=?",
                (ref["id"], ref["revision"]),
            ).fetchone()
            if row:
                source_versions.append(json.loads(row[0]))
        return self.response(
            work=work,
            contributions=contributions,
            memberships=memberships,
            topics=[
                {k: t[k] for k in ("id", "title", "pillar")}
                for t in self.manifest["dossiers"]
                if t["id"] in work["topic_ids"]
            ],
            people=[
                json.loads(r[0])
                for p in work.get("people", [])
                if (
                    r := self.db.execute(
                        "SELECT payload FROM people WHERE snapshot=? AND id=?",
                        (self.release, p),
                    ).fetchone()
                )
            ],
            sources=source_versions,
            relations=related,
            shared_insights=shared,
            notice="Catalog provenance identifies the work. Insight support and discovery credit are separate. Shared insights are navigation, not historical influence.",
        )

    def search(
        self, query="", pillar=None, human=False, limit=40, match_any=False, offset=0
    ):
        """Rank direct text matches first, then explicit catalog memberships.

        Navigation expansion is one hop only. It never invents a scientific
        connection or repeatedly expands a broad query through the entire atlas.
        """
        limit = min(max(int(limit), 1), 100)
        offset = max(int(offset), 0)
        plan = self.search_plan(query)
        terms = retrieval.tokens(query)
        empty = {
            "results": [],
            "people": [],
            "topics": [],
            "works": [],
            "totals": {k: 0 for k in ("ideas", "people", "topics", "works")},
            "offset": offset,
            "limit": limit,
            "search_interpretation": plan,
        }
        if query.strip() and not terms:
            return self.response(**empty)
        if (
            human
            and not self.db.execute(
                "SELECT 1 FROM records r JOIN members m ON r.id=m.id AND r.revision=m.revision WHERE m.snapshot=? AND r.type='review' AND json_extract(r.payload,'$.reviewer_type')='human' AND json_extract(r.payload,'$.judgment')='accepted' LIMIT 1",
                (self.release,),
            ).fetchone()
        ):
            return self.response(**empty)
        person_ids = (
            self.catalog_matches(query, "person", plan["queries"]) if terms else []
        )
        work_ids = self.catalog_matches(query, "work", plan["queries"]) if terms else []
        topic_ids = (
            self.catalog_matches(query, "topic", plan["queries"]) if terms else []
        )
        params = [self.release]
        source = "records r JOIN members m ON r.id=m.id AND r.revision=m.revision"
        where = "m.snapshot=? AND r.type='contribution' AND json_extract(r.payload,'$.publication_state') IN ('exploratory','reviewed') AND json_extract(r.payload,'$.machine_screening')='passed'"
        order = "r.id"
        order_params = []
        if terms:
            source += " JOIN search ON search.id=r.id AND search.snapshot=m.snapshot"
            where += " AND search MATCH ?"
            params.append(retrieval.expression(plan["queries"], match_any))
            order = "CASE WHEN instr(lower(search.title),lower(?))=1 THEN 0 WHEN instr(lower(search.title),lower(?))>0 THEN 1 ELSE 2 END,bm25(search,0,0,8,3,1),r.id"
            order_params = [query.strip(), query.strip()]
        if pillar:
            where += " AND json_extract(r.payload,'$.pillar')=?"
            params.append(pillar)
        direct = [
            r[0]
            for r in self.db.execute(
                "SELECT r.id FROM " + source + " WHERE " + where + " ORDER BY " + order,
                (*params, *order_params),
            )
        ]
        people = {
            r[0]: json.loads(r[1])
            for r in self.db.execute(
                "SELECT id,payload FROM people WHERE snapshot=?", (self.release,)
            )
        }
        works = {
            r[0]: json.loads(r[1])
            for r in self.db.execute(
                "SELECT id,payload FROM works WHERE snapshot=?", (self.release,)
            )
        }
        person_ids = [
            i for i in person_ids if not pillar or pillar in people[i]["subjects"]
        ]
        work_ids = [i for i in work_ids if not pillar or pillar in works[i]["subjects"]]
        credits = list(
            self.db.execute(
                "SELECT person,id FROM person_members WHERE snapshot=?", (self.release,)
            )
        )
        memberships = list(
            self.db.execute(
                "SELECT work,id FROM work_members WHERE snapshot=?", (self.release,)
            )
        )
        named_people = set(person_ids)
        selected_works = {
            w
            for w, p in self.db.execute(
                "SELECT work,person FROM work_people WHERE snapshot=?", (self.release,)
            )
            if p in named_people and (not pillar or pillar in works[w]["subjects"])
        }
        work_ids += sorted(selected_works - set(work_ids))
        matched_people, matched_works = named_people, set(work_ids)
        direct_ids = set(direct)
        related = {n for p, n in credits if p in matched_people} | {
            n for w, n in memberships if w in matched_works
        }
        eligible = {
            r[0]
            for r in self.db.execute(
                "SELECT r.id,json_extract(r.payload,'$.pillar'),json_extract(r.payload,'$.content_hash') FROM records r JOIN members m ON r.id=m.id AND r.revision=m.revision WHERE m.snapshot=? AND r.type='contribution' AND json_extract(r.payload,'$.publication_state') IN ('exploratory','reviewed') AND json_extract(r.payload,'$.machine_screening')='passed'",
                (self.release,),
            )
            if (not pillar or r[1] == pillar)
            and (
                not human or self.human_state({"content_hash": r[2]}) != "not_reviewed"
            )
        }
        idea_ids = [i for i in direct if i in eligible] + sorted(
            (related - direct_ids) & eligible
        )
        # Direct idea matches expose their works and credited individuals. These
        # additions do not themselves generate a second wave of idea matches.
        work_ids += sorted(
            {
                w
                for w, n in memberships
                if n in direct_ids
                and w not in matched_works
                and (not pillar or pillar in works[w]["subjects"])
            }
        )
        person_ids += sorted(
            {
                p
                for p, n in credits
                if n in direct_ids
                and p not in matched_people
                and (not pillar or pillar in people[p]["subjects"])
            }
        )
        work_people = {p for w in matched_works for p in works[w].get("people", [])}
        person_ids += sorted(work_people - set(person_ids))
        if human:
            allowed_works = {w for w, n in memberships if n in eligible}
            allowed_people = {p for p, n in credits if n in eligible}
            work_ids = [w for w in work_ids if w in allowed_works]
            person_ids = [p for p in person_ids if p in allowed_people]
        matched_idea_ids = set(idea_ids)
        linked_topics = {t for w in work_ids for t in works[w]["topic_ids"]} | {
            t
            for t, n in self.db.execute(
                "SELECT topic,id FROM topic_members WHERE snapshot=?", (self.release,)
            )
            if n in matched_idea_ids
        }
        topic_ids += sorted(linked_topics - set(topic_ids))
        if human:
            allowed_topics = {
                t
                for t, n in self.db.execute(
                    "SELECT topic,id FROM topic_members WHERE snapshot=?",
                    (self.release,),
                )
                if n in eligible
            }
            topic_ids = [t for t in topic_ids if t in allowed_topics]
        topics = {t["id"]: t for t in self.manifest["dossiers"]}
        topic_ids = [
            t for t in topic_ids if not pillar or topics[t]["pillar"] == pillar
        ]
        return self.response(
            results=[
                self.get(i, "contribution") for i in idea_ids[offset : offset + limit]
            ],
            people=[people[i] for i in person_ids[offset : offset + limit]],
            works=[works[i] for i in work_ids[offset : offset + limit]],
            topics=[
                {k: topics[i][k] for k in ("id", "title", "pillar")}
                for i in topic_ids[offset : offset + limit]
            ],
            totals={
                "ideas": len(idea_ids),
                "people": len(person_ids),
                "works": len(work_ids),
                "topics": len(topic_ids),
            },
            offset=offset,
            limit=limit,
            search_interpretation=plan,
        )

    def dossiers(self):
        rows = []
        # Decode subject records once, without loading every source and review.
        subject_records = [
            json.loads(row[0])
            for row in self.db.execute(
                "SELECT json_object('id',r.id,'revision',r.revision,'type',r.type,"
                "'content_hash',json_extract(r.payload,'$.content_hash'),"
                "'anchors',json_extract(r.payload,'$.anchors'),"
                "'premises',json_extract(r.payload,'$.premises'),"
                "'conclusion',json_extract(r.payload,'$.conclusion'),"
                "'layer',json_extract(r.payload,'$.layer'),'predicate',json_extract(r.payload,'$.predicate')) "
                "FROM records r JOIN members m ON r.id=m.id AND r.revision=m.revision "
                "WHERE m.snapshot=? AND r.type IN ('contribution','relation') "
                "AND json_extract(r.payload,'$.publication_state') IN ('exploratory','reviewed') "
                "AND json_extract(r.payload,'$.machine_screening')='passed'",
                (self.release,),
            )
        ]
        members_by_topic = {}
        by_id = {r["id"]: r for r in subject_records if r["type"] == "contribution"}
        for topic, id in self.db.execute(
            "SELECT topic,id FROM topic_members WHERE snapshot=?", (self.release,)
        ):
            if id in by_id:
                members_by_topic.setdefault(topic, []).append(by_id[id])
        # Intersect membership sets once per relation instead of scanning all
        # relations for every topic (the expanded catalogue has thousands).
        node_topics = {}
        for topic, members in members_by_topic.items():
            for n in members:
                node_topics.setdefault(n["id"], set()).add(topic)
        edges_by_topic = {}
        for edge in (r for r in subject_records if r["type"] == "relation"):
            endpoints = [*edge["premises"], edge["conclusion"]]
            common = set.intersection(
                *(node_topics.get(x["id"], set()) for x in endpoints)
            )
            for topic in common:
                edges_by_topic.setdefault(topic, []).append(edge)
        works_by_topic = {}
        for topic, work in self.db.execute(
            "SELECT topic,work FROM work_topics WHERE snapshot=?", (self.release,)
        ):
            works_by_topic.setdefault(topic, []).append(work)
        for d in self.manifest["dossiers"]:
            members = members_by_topic.get(d["id"], [])
            ids = {r["id"] for r in members}
            edges = edges_by_topic.get(d["id"], [])
            connected = {
                ref["id"] for e in edges for ref in [*e["premises"], e["conclusion"]]
            }
            checklist = [
                {**c, "supported": any(id in ids for id in c.get("contributions", []))}
                for c in d["checklist"]
            ]
            status = (
                "initial_neighborhood"
                if len(members) >= 8
                and d.get("endpoint") in ids
                and all(
                    d.get("search_outcomes", {}).get(k, "pending").strip()
                    not in {"", "pending"}
                    for k in ("alternatives", "limitations", "attribution")
                )
                else "in_progress"
                if members
                else "unresolved"
            )
            rows.append(
                {
                    **d,
                    "status": status,
                    "endpoint": d.get("endpoint") if d.get("endpoint") in ids else None,
                    "endpoint_revision": next(
                        (
                            n["revision"]
                            for n in members
                            if n["id"] == d.get("endpoint")
                        ),
                        None,
                    ),
                    "declared_endpoint": d.get("endpoint"),
                    "checklist": checklist,
                    "work_count": len(works_by_topic.get(d["id"], [])),
                    "work_ids": works_by_topic.get(d["id"], []),
                    "contribution_count": len(members),
                    "relation_count": len(edges),
                    "isolated_contribution_count": len(ids - connected),
                    "source_count": len(
                        {a["source_id"] for n in members for a in n.get("anchors", [])}
                    ),
                    "historical_relation_count": sum(
                        e["layer"] == "historical" for e in edges
                    ),
                    "boundary_relation_count": sum(
                        e["predicate"] in {"bounded_by", "challenges"} for e in edges
                    ),
                    "checklist_coverage": sum(c["supported"] for c in checklist)
                    / len(checklist)
                    if checklist
                    else 0,
                    "human_review_count": sum(
                        self.human_state(r) != "not_reviewed" for r in members
                    ),
                }
            )
        return self.response(dossiers=rows)

    def neighborhood(
        self,
        dossier=None,
        seed=None,
        layers=None,
        human=False,
        limit=80,
        hops=1,
        direction="both",
    ):
        limit = min(max(int(limit), 1), 200)
        hops = min(max(int(hops), 0), 6)
        valid_layers = {p[0] for p in PREDICATES.values()}
        layers = set(valid_layers if layers is None else layers)
        if not layers <= valid_layers:
            raise ValueError("Unknown relationship layer")
        if direction not in ("both", "ancestors", "descendants"):
            raise ValueError("Invalid traversal direction")
        # Eligibility needs identities and review hashes, not the full corpus text.
        # Decode only the bounded neighborhood returned to the reader.
        available = {
            id
            for id, hash in self.db.execute(
                "SELECT r.id,json_extract(r.payload,'$.content_hash') FROM records r JOIN members m ON r.id=m.id AND r.revision=m.revision WHERE m.snapshot=? AND r.type='contribution' AND json_extract(r.payload,'$.publication_state') IN ('exploratory','reviewed') AND json_extract(r.payload,'$.machine_screening')='passed'",
                (self.release,),
            )
            if not human or self.human_state({"content_hash": hash}) != "not_reviewed"
        }

        def eligible(ids):
            return [
                r
                for r in self.adjacent_relations(ids, layers)
                if (not human or self.human_state(r) != "not_reviewed")
                and all(x["id"] in available for x in [*r["premises"], r["conclusion"]])
            ]

        available_count = None
        if seed:
            if seed not in available:
                raise KeyError(seed)
            selected = {seed}
            for _ in range(hops):
                additions = set()
                for e in eligible(selected):
                    premises = {x["id"] for x in e["premises"]}
                    conclusion = e["conclusion"]["id"]
                    symmetric = PREDICATES[e["predicate"]][1]
                    if (
                        (direction in ("both", "ancestors") or symmetric)
                        and conclusion in selected
                    ) or (
                        (direction in ("both", "descendants") or symmetric)
                        and premises & selected
                    ):
                        additions.update(premises | {conclusion})
                for id in sorted(additions):
                    if len(selected) < limit:
                        selected.add(id)
        elif dossier:
            endpoint = next(
                (
                    d.get("endpoint")
                    for d in self.manifest["dossiers"]
                    if d["id"] == dossier
                ),
                None,
            )
            members = {
                row[0]
                for row in self.db.execute(
                    "SELECT id FROM topic_members WHERE snapshot=? AND topic=?",
                    (self.release, dossier),
                )
                if row[0] in available
            }
            neighbors = {id: set() for id in members}
            # Rank by actual local connections, independent of the visible layer
            # toggles. This is navigation distance, never a transitive proof.
            for edge in self.adjacent_relations(members, valid_layers):
                ends = {p["id"] for p in [*edge["premises"], edge["conclusion"]]}
                if ends <= members:
                    for id in ends:
                        neighbors[id].update(ends - {id})
            distances = {endpoint: 0} if endpoint in members else {}
            frontier = set(distances)
            depth = 0
            while frontier:
                depth += 1
                frontier = {
                    n for id in frontier for n in neighbors[id]
                } - distances.keys()
                distances.update({id: depth for id in frontier})
            ordered = sorted(
                members,
                key=lambda id: (
                    distances.get(id, float("inf")),
                    -len(neighbors[id]),
                    id,
                ),
            )
            available_count = len(ordered)
            selected = set(ordered[:limit])
        else:
            selected = set(sorted(available)[: min(limit, 40)])
        included = [
            e
            for e in eligible(selected)
            if e["conclusion"]["id"] in selected
            and all(x["id"] in selected for x in e["premises"])
        ]
        return self.response(
            contributions=[self.get(id, "contribution") for id in sorted(selected)],
            relations=included,
            layers=sorted(layers),
            limit=limit,
            available_count=available_count,
            notice="Paths describe the recorded relationship layers, not exclusive ancestry or transitive proof.",
        )

    def brief(self, query, limit=12, policy=None, dossier=None):
        if dossier:
            assignment = next(
                (d for d in self.manifest["dossiers"] if d["id"] == dossier), None
            )
            if assignment is None:
                raise ValueError("Unknown dossier")
            topic_ids = {
                row[0]
                for row in self.db.execute(
                    "SELECT id FROM topic_members WHERE snapshot=? AND topic=?",
                    (self.release, dossier),
                )
            }
            primary = [self.get(id, "contribution") for id in topic_ids]
            primary.sort(key=lambda r: (r["id"] != assignment.get("endpoint"), r["id"]))
            primary = primary[:limit]
        else:
            primary = self.search(query, limit=limit)["results"]
            if not primary and query.strip():
                primary = self.search(query, limit=limit, match_any=True)["results"]
        ids = {r["id"] for r in primary}
        edges = self.adjacent_relations(ids, {p[0] for p in PREDICATES.values()})
        # Preserve complete joint-premise groups, and preferentially include boundaries.
        edges.sort(
            key=lambda r: (r["predicate"] not in ("bounded_by", "challenges"), r["id"])
        )
        edges = edges[:40]
        closure = ids | {
            x["id"] for e in edges for x in [*e["premises"], e["conclusion"]]
        }
        contributions = [self.get(id, "contribution") for id in sorted(closure)]
        hashes = [r["content_hash"] for r in [*contributions, *edges]]
        placeholders = ",".join("?" for _ in hashes)
        reviews = (
            [
                json.loads(row[0])
                for row in self.db.execute(
                    "SELECT r.payload FROM records r JOIN members m ON r.id=m.id AND r.revision=m.revision "
                    "WHERE m.snapshot=? AND r.type='review' AND json_extract(r.payload,'$.target.content_hash') IN ("
                    + placeholders
                    + ") ORDER BY r.id",
                    (self.release, *hashes),
                )
            ]
            if hashes
            else []
        )
        memberships = [
            {
                "contribution": {k: r[k] for k in ("id", "revision", "content_hash")},
                "topics": self.topics_for(r["id"]),
            }
            for r in contributions
        ]
        navigation_anchors = [
            a for m in memberships for t in m["topics"] for a in t.get("anchors", [])
        ]
        anchors = [a for r in [*contributions, *edges] for a in r.get("anchors", [])]
        anchors.extend(navigation_anchors)
        source_refs = {(a["source_id"], a["source_revision"]) for a in anchors}
        works = {w["id"]: w for n in contributions for w in self.works_for(n["id"])}
        work_memberships = [
            json.loads(row[0])
            for n in contributions
            for row in self.db.execute(
                "SELECT payload FROM work_members WHERE snapshot=? AND id=?",
                (self.release, n["id"]),
            )
        ]
        source_refs.update(
            (r["id"], r["revision"])
            for w in works.values()
            for r in w.get("source_refs", [])
        )
        sources = []
        for source_id, revision in sorted(source_refs):
            row = self.db.execute(
                "SELECT payload FROM records WHERE id=? AND revision=?",
                (source_id, revision),
            ).fetchone()
            if row:
                sources.append(json.loads(row[0]))
        dossiers = {d["id"] for r in contributions for d in self.topics_for(r["id"])}
        return self.response(
            query=query,
            relevant_contributions=contributions,
            supported_relations=edges,
            source_anchors=anchors,
            sources=sources,
            topic_memberships=memberships,
            works=list(works.values()),
            work_insight_memberships=work_memberships,
            navigation_source_anchors=navigation_anchors,
            assumptions_and_scope=[
                {"id": r["id"], "assumptions": r["assumptions"], "limits": r["limits"]}
                for r in contributions
            ],
            counterevidence_and_alternatives=[
                r
                for r in edges
                if r["predicate"]
                in ("challenges", "bounded_by", "independent_formulation_of")
            ],
            review_and_uncertainty_states=[
                {
                    "id": r["id"],
                    "revision": r["revision"],
                    "human_review": self.human_state(r),
                    "machine_screening": r["machine_screening"],
                    "scientific_standing": r["scientific_standing"],
                }
                for r in contributions
            ],
            reviews=reviews,
            selection={
                "primary_limit": limit,
                "relation_limit": 40,
                "dependency_closure": "Every selected relation endpoint and source revision is included; this is a bounded brief, not all ancestry.",
            },
            unresolved_questions=[
                g
                for d in self.manifest["dossiers"]
                if d["id"] in dossiers
                for g in d["gaps"]
            ],
            normative_sources_considered=[
                r["id"] for r in contributions if r["kind"] == "normative_argument"
            ],
            applicable_human_supplied_policy_profile=policy,
            permitted_action_scope="read_only",
            notice="This evidence brief is not authorization and does not establish expert validation.",
        )

    def changes(self, from_release):
        row = self.db.execute(
            "SELECT payload FROM snapshots WHERE id=?", (from_release,)
        ).fetchone()
        if not row:
            raise ValueError("Unknown comparison snapshot")
        prior_manifest = json.loads(row[0])
        old = {r["id"]: r for r in prior_manifest["record_refs"]}
        catalog_changes = {}
        for kind in ("works", "people", "dossiers"):
            before = {r["id"]: r for r in prior_manifest.get(kind, [])}
            after = {r["id"]: r for r in self.manifest.get(kind, [])}
            catalog_changes[kind] = {
                "added": sorted(after.keys() - before.keys()),
                "removed": sorted(before.keys() - after.keys()),
                "changed": sorted(
                    k
                    for k in before.keys() & after.keys()
                    if digest(before[k]) != digest(after[k])
                ),
            }
        new = {r["id"]: r for r in self.manifest["record_refs"]}

        def describe(ref):
            row = self.db.execute(
                "SELECT payload FROM records WHERE id=? AND revision=?",
                (ref["id"], ref["revision"]),
            ).fetchone()
            record = json.loads(row[0])
            return {
                **ref,
                "type": record["type"],
                "title": record.get("title")
                or record.get("predicate", "").replace("_", " ")
                or "Review of " + record.get("target", {}).get("id", "record"),
                "publication_state": record.get("publication_state"),
                "visible": visible(record)
                if record["type"] in ("contribution", "relation")
                else False,
            }

        return self.response(
            from_release=from_release,
            catalog_changes=catalog_changes,
            added=[describe(new[k]) for k in sorted(new.keys() - old.keys())],
            removed=[describe(old[k]) for k in sorted(old.keys() - new.keys())],
            changed=[
                {"before": describe(old[k]), "after": describe(new[k])}
                for k in sorted(new.keys() & old.keys())
                if old[k]["content_hash"] != new[k]["content_hash"]
            ],
        )

    def info(self):
        counts = {kind: 0 for kind in ("contribution", "relation", "source", "review")}
        for kind, count in self.db.execute(
            "SELECT r.type, COUNT(*) FROM records r JOIN members m ON r.id=m.id AND r.revision=m.revision "
            "WHERE m.snapshot=? AND (r.type NOT IN ('contribution','relation') OR "
            "(json_extract(r.payload,'$.publication_state') IN ('exploratory','reviewed') "
            "AND json_extract(r.payload,'$.machine_screening')='passed')) GROUP BY r.type",
            (self.release,),
        ):
            counts[kind] = count
        human_reviewed = sum(
            self.human_state({"content_hash": row[0]}) != "not_reviewed"
            for row in self.db.execute(
                "SELECT json_extract(r.payload,'$.content_hash') FROM records r "
                "JOIN members m ON r.id=m.id AND r.revision=m.revision "
                "WHERE m.snapshot=? AND r.type='contribution' AND "
                "json_extract(r.payload,'$.publication_state') IN ('exploratory','reviewed') "
                "AND json_extract(r.payload,'$.machine_screening')='passed'",
                (self.release,),
            )
        )
        return self.response(
            subject_counts=dict(
                self.db.execute(
                    "SELECT json_extract(r.payload,'$.pillar'),COUNT(*) FROM records r JOIN members m ON r.id=m.id AND r.revision=m.revision WHERE m.snapshot=? AND r.type='contribution' AND json_extract(r.payload,'$.publication_state') IN ('exploratory','reviewed') AND json_extract(r.payload,'$.machine_screening')='passed' GROUP BY json_extract(r.payload,'$.pillar')",
                    (self.release,),
                )
            ),
            counts=counts,
            catalog_counts={
                "works": self.db.execute(
                    "SELECT COUNT(*) FROM works WHERE snapshot=?", (self.release,)
                ).fetchone()[0],
                "people": self.db.execute(
                    "SELECT COUNT(*) FROM people WHERE snapshot=?", (self.release,)
                ).fetchone()[0],
                "topics": len(self.manifest["dossiers"]),
                "works_with_insights": self.db.execute(
                    "SELECT COUNT(DISTINCT work) FROM work_members WHERE snapshot=?",
                    (self.release,),
                ).fetchone()[0],
            },
            pillars=PILLARS,
            predicates={
                k: {"layer": v[0], "symmetric": v[1], "label": v[2], "meaning": v[3]}
                for k, v in PREDICATES.items()
            },
            releases=[
                r[0] for r in self.db.execute("SELECT id FROM snapshots ORDER BY id")
            ],
            tours=self.manifest.get("tours", []),
            maturity="exploratory",
            current_release_id=self.db.execute(
                "SELECT value FROM metadata WHERE key='current_release'"
            ).fetchone()[0],
            human_reviewed=human_reviewed,
        )
