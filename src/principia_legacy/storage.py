"""Deterministic compilation into a read-only, snapshot-aware SQLite atlas."""

import json
import sqlite3
from pathlib import Path
from .common import digest, read_json, read_lines
from .records import PILLARS, PREDICATES, validate, visible
from .catalog import navigation_index


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
        CREATE VIRTUAL TABLE catalog_search USING fts5(snapshot UNINDEXED,id UNINDEXED,kind UNINDEXED,title,description,tokenize='unicode61 remove_diacritics 2');
        """)
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
                if record and record["type"] == "relation" and visible(record):
                    if any(
                        membership.get(endpoint["id"]) != endpoint["revision"]
                        for endpoint in [*record["premises"], record["conclusion"]]
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
        row = self.db.execute(
            "SELECT payload FROM snapshots WHERE id=?", (self.release,)
        ).fetchone()
        if not row:
            self.db.close()
            raise ValueError("Unknown release snapshot")
        self.manifest = json.loads(row[0])
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
            "snapshot_hash": digest(self.manifest),
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
        return self.response(
            person=person,
            contributions=contributions,
            topics=[
                {k: d[k] for k in ("id", "title", "pillar")}
                for d in self.manifest["dossiers"]
                if d["id"] in topic_ids
            ],
            notice="Recorded credit and navigational topic membership do not establish exclusive authorship, priority, or influence. Biographical sources are identified separately.",
        )

    def people(self, query="", limit=60, offset=0, human=False):
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

    def catalog_matches(self, query, kind):
        import re

        terms = re.findall(r"[^\W_]+", query, flags=re.UNICODE)[:16]
        if not terms:
            return []
        expression = " AND ".join('"' + t.replace('"', '""') + '"*' for t in terms)
        return [
            r[0]
            for r in self.db.execute(
                "SELECT id FROM catalog_search WHERE catalog_search MATCH ? AND snapshot=? AND kind=? ORDER BY bm25(catalog_search)",
                (expression, self.release, kind),
            )
        ]

    def search(
        self, query="", pillar=None, human=False, limit=40, match_any=False, offset=0
    ):
        import re

        limit = min(max(int(limit), 1), 100)
        offset = max(int(offset), 0)
        if len(query) > 500:
            raise ValueError("Search query is too long")
        empty = dict(
            results=[],
            people=[],
            topics=[],
            totals={"ideas": 0, "people": 0, "topics": 0},
            offset=offset,
            limit=limit,
        )
        terms = re.findall(r"[^\W_]+", query, flags=re.UNICODE)[:16]
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
        params = [self.release]
        source = "records r JOIN members m ON r.id=m.id AND r.revision=m.revision"
        where = "m.snapshot=? AND r.type='contribution' AND json_extract(r.payload,'$.publication_state') IN ('exploratory','reviewed') AND json_extract(r.payload,'$.machine_screening')='passed'"
        order = "r.id"
        if terms:
            source += " JOIN search ON search.id=r.id AND search.snapshot=m.snapshot"
            where += " AND search MATCH ?"
            params.append(
                (" OR " if match_any else " AND ").join('"' + t + '"*' for t in terms)
            )
            order = "bm25(search,0,0,8,3,1),r.id"
        if pillar:
            where += " AND json_extract(r.payload,'$.pillar')=?"
            params.append(pillar)
        # Count in SQLite and decode only the requested page for ordinary search.
        sql = " FROM " + source + " WHERE " + where
        if human:
            candidates = [
                json.loads(r[0])
                for r in self.db.execute(
                    "SELECT r.payload" + sql + " ORDER BY " + order, params
                )
            ]
            candidates = [
                n for n in candidates if self.human_state(n) != "not_reviewed"
            ]
            matches = candidates[offset : offset + limit]
            total = len(candidates)
        else:
            total = self.db.execute("SELECT COUNT(*)" + sql, params).fetchone()[0]
            matches = [
                json.loads(r[0])
                for r in self.db.execute(
                    "SELECT r.payload"
                    + sql
                    + " ORDER BY "
                    + order
                    + " LIMIT ? OFFSET ?",
                    (*params, limit, offset),
                )
            ]
        people = []
        for id in self.catalog_matches(query, "person") if terms else []:
            p = json.loads(
                self.db.execute(
                    "SELECT payload FROM people WHERE snapshot=? AND id=?",
                    (self.release, id),
                ).fetchone()[0]
            )
            if (not pillar or pillar in p["subjects"]) and (
                not human or self.person(id, True)["contributions"]
            ):
                people.append(p)
        topic_ids = set(self.catalog_matches(query, "topic")) if terms else set()
        topics = [
            {k: d[k] for k in ("id", "title", "pillar")}
            for d in self.manifest["dossiers"]
            if d["id"] in topic_ids and (not pillar or d["pillar"] == pillar)
        ]
        if human:
            reviewed_topics = {
                t["id"]
                for n in self.contributions()
                if visible(n) and self.human_state(n) != "not_reviewed"
                for t in self.topics_for(n["id"])
            }
            topics = [t for t in topics if t["id"] in reviewed_topics]
        return self.response(
            results=matches,
            people=people[offset : offset + limit],
            topics=topics[offset : offset + limit],
            offset=offset,
            limit=limit,
            totals={"ideas": total, "people": len(people), "topics": len(topics)},
        )

    def dossiers(self):
        rows = []
        # Decode subject records once, without loading every source and review.
        subject_records = [
            json.loads(row[0])
            for row in self.db.execute(
                "SELECT r.payload FROM records r JOIN members m ON r.id=m.id AND r.revision=m.revision "
                "WHERE m.snapshot=? AND r.type IN ('contribution','relation')",
                (self.release,),
            )
        ]
        subject_records = [r for r in subject_records if visible(r)]
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
        for d in self.manifest["dossiers"]:
            members = members_by_topic.get(d["id"], [])
            ids = {r["id"] for r in members}
            edges = edges_by_topic.get(d["id"], [])
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
                    "contribution_count": len(members),
                    "relation_count": len(edges),
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
        old = {r["id"]: r for r in json.loads(row[0])["record_refs"]}
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
            pillars=PILLARS,
            predicates={
                k: {"layer": v[0], "symmetric": v[1], "label": v[2]}
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
