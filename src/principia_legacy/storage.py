"""Snapshot-pinned record inspectors and reader facade; all operations are read-only."""

import json
import sqlite3
from collections import Counter, OrderedDict
from pathlib import Path
from threading import Lock

from . import retrieval
from .common import decode_snapshot, digest
from .compiler import (
    build as build,
)
from .compiler import (
    corpus as corpus,
)
from .compiler import (
    latest_records as latest_records,
)
from .compiler import (
    manifest as manifest,
)
from .graph_queries import GraphQueries
from .queries import ReaderQueries
from .records import PILLARS, PREDICATES, visible

_snapshots = OrderedDict()
_snapshot_lock = Lock()


class Atlas(ReaderQueries, GraphQueries):
    def __init__(self, root, release=None):
        self.root = Path(root)
        path = self.root / "build/atlas.sqlite"
        if not path.exists():
            raise ValueError("Atlas database missing. Run build --offline first.")
        # Atomic compilation can replace the file while a reader opens it. Cache
        # context only when the connection and stat identify the same generation.
        for _ in range(3):
            before = path.stat()
            self.db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
            self.db.execute("PRAGMA query_only=ON")
            stat = path.stat()
            if (before.st_ino, before.st_mtime_ns, before.st_size) == (
                stat.st_ino,
                stat.st_mtime_ns,
                stat.st_size,
            ):
                break
            self.db.close()
        else:
            raise ValueError("Atlas is being activated. Please retry the request.")
        self.release = (
            release
            or self.db.execute(
                "SELECT value FROM metadata WHERE key='current_release'"
            ).fetchone()[0]
        )
        self._manifest = None
        try:
            key = (
                str(path.resolve()),
                stat.st_ino,
                stat.st_mtime_ns,
                stat.st_size,
                self.release,
            )
            with _snapshot_lock:
                if key not in _snapshots:
                    row = self.db.execute(
                        "SELECT payload,hash,info FROM snapshot_context WHERE snapshot=?",
                        (self.release,),
                    ).fetchone()
                    if not row:
                        raise ValueError("Unknown release snapshot")
                    _snapshots[key] = (json.loads(row[0]), row[1], json.loads(row[2]))
                    while len(_snapshots) > 2:
                        _snapshots.popitem(last=False)
                else:
                    _snapshots.move_to_end(key)
                self.context, self.snapshot_hash, self._info = _snapshots[key]
        except Exception:
            self.db.close()
            raise
        self._records = None
        self._human_states = None

    @property
    def manifest(self):
        """Load the full immutable manifest only for exports and comparisons."""
        if self._manifest is None:
            row = self.db.execute(
                "SELECT payload FROM snapshots WHERE id=?", (self.release,)
            ).fetchone()
            self._manifest = decode_snapshot(row[0])
        return self._manifest

    @manifest.setter
    def manifest(self, value):
        self._manifest = value

    def topic_metadata(self, ids):
        values = []
        ids = sorted(set(ids))
        for offset in range(0, len(ids), 400):
            batch = ids[offset : offset + 400]
            marks = ",".join("?" for _ in batch)
            values.extend(
                json.loads(r[0])
                for r in self.db.execute(
                    f"SELECT payload FROM topic_summaries WHERE snapshot=? AND id IN ({marks}) ORDER BY id",
                    (self.release, *batch),
                )
            )
        return values

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
                        for n in self.get_many(f["contributions"], "contribution")
                        if visible(n)
                    ],
                }
                for f in self.context.get("idea_families", [])
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
                    for k, v in json.loads(row[3] or "{}").items()
                    if k in {"anchors", "screening_request_id", "source_url"}
                    and row[2] != "record"
                },
            }
            for row in self.db.execute(
                "SELECT m.topic,m.reason,m.origin,e.payload FROM topic_members m LEFT JOIN topic_evidence e ON e.snapshot=m.snapshot AND e.topic=m.topic AND e.id=m.id WHERE m.snapshot=? AND m.id=?",
                (self.release, id),
            )
        }
        return [
            {**{k: d[k] for k in ("id", "title", "pillar")}, **memberships[d["id"]]}
            for d in self.topic_metadata(memberships)
        ]

    def person(self, id, human=False, limit=None, offset=0, cursor=None):
        row = self.db.execute(
            "SELECT payload FROM people WHERE snapshot=? AND id=?", (self.release, id)
        ).fetchone()
        if not row:
            raise KeyError(id)
        person = json.loads(row[0])
        where = (
            " FROM person_members m JOIN visible_nodes n ON n.snapshot=m.snapshot AND n.id=m.id WHERE m.snapshot=? AND m.person=?"
            + (" AND n.human!='not_reviewed'" if human else "")
        )
        total = self.db.execute(
            "SELECT COUNT(*)" + where, (self.release, id)
        ).fetchone()[0]
        offset, page_limit, signature = self._page(
            offset, limit or 40, cursor, ["person-insights", id, human]
        )
        page = self.db.execute(
            "SELECT n.id,m.credit"
            + where
            + " ORDER BY n.year IS NULL,n.year,n.title,n.id LIMIT ? OFFSET ?",
            (self.release, id, page_limit, offset),
        ).fetchall()
        credits = {r[0]: json.loads(r[1]) for r in page}
        contributions = [
            {**r, "credit": credits[r["id"]]}
            for r in self.get_many(credits, "contribution")
        ]
        topic_ids = {
            r[0]
            for r in self.db.execute(
                "SELECT DISTINCT t.topic FROM topic_members t JOIN person_members p ON p.snapshot=t.snapshot AND p.id=t.id JOIN visible_nodes n ON n.snapshot=p.snapshot AND n.id=p.id WHERE p.snapshot=? AND p.person=?"
                + (" AND n.human!='not_reviewed'" if human else ""),
                (self.release, id),
            )
        }
        works = self.works(person=id, human=human, limit=100)["works"]
        topic_ids.update(
            r[0]
            for r in self.db.execute(
                "SELECT DISTINCT t.topic FROM work_topics t JOIN work_people p ON p.snapshot=t.snapshot AND p.work=t.work WHERE p.snapshot=? AND p.person=?"
                + (
                    " AND EXISTS(SELECT 1 FROM work_members m JOIN visible_nodes n ON n.snapshot=m.snapshot AND n.id=m.id WHERE m.snapshot=p.snapshot AND m.work=p.work AND n.human!='not_reviewed')"
                    if human
                    else ""
                ),
                (self.release, id),
            )
        )
        return self.response(
            person=person,
            contribution_total=total,
            next_cursor=self._next(offset, page_limit, total, signature),
            offset=offset,
            limit=page_limit,
            contributions=contributions,
            works=works,
            topics=[
                {k: d[k] for k in ("id", "title", "pillar")}
                for d in self.topic_metadata(topic_ids)
            ],
            notice="Recorded credit and navigational topic membership do not establish exclusive authorship, priority, or influence. Biographical sources are identified separately.",
        )

    def search_plan(self, query):
        if len(query) > 500:
            raise ValueError("Search query is too long")
        return retrieval.plan(
            self.db, self.release, query, self.context.get("search_concepts", [])
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

    def work(self, id, human=False, limit=None, offset=0, cursor=None):
        row = self.db.execute(
            "SELECT payload FROM works WHERE snapshot=? AND id=?", (self.release, id)
        ).fetchone()
        if not row:
            raise KeyError(id)
        work = json.loads(row[0])
        where = (
            " FROM work_members m JOIN visible_nodes n ON n.snapshot=m.snapshot AND n.id=m.id WHERE m.snapshot=? AND m.work=?"
            + (" AND n.human!='not_reviewed'" if human else "")
        )
        total = self.db.execute(
            "SELECT COUNT(*)" + where, (self.release, id)
        ).fetchone()[0]
        offset, page_limit, signature = self._page(
            offset, limit or 40, cursor, ["work-insights", id, human]
        )
        page = self.db.execute(
            "SELECT n.id,m.payload" + where + " ORDER BY n.id LIMIT ? OFFSET ?",
            (self.release, id, page_limit, offset),
        ).fetchall()
        contributions = self.get_many([r[0] for r in page], "contribution")
        memberships = [json.loads(r[1]) for r in page]
        related = []
        for link in (
            json.loads(r[0])
            for r in self.db.execute(
                "SELECT payload FROM work_links WHERE snapshot=? AND (json_extract(payload,'$.from.id')=? OR json_extract(payload,'$.to.id')=?)",
                (self.release, id, id),
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
        shared_filter = (
            " AND EXISTS(SELECT 1 FROM visible_nodes n WHERE n.snapshot=a.snapshot AND n.id=a.id AND n.human!='not_reviewed')"
            if human
            else ""
        )
        shared = [
            {"work": json.loads(row[0]), "insight_count": row[1]}
            for row in self.db.execute(
                "SELECT w.payload,COUNT(*) FROM work_members a JOIN work_members b ON a.snapshot=b.snapshot AND a.id=b.id AND a.work!=b.work JOIN works w ON w.snapshot=b.snapshot AND w.id=b.work WHERE a.snapshot=? AND a.work=?"
                + shared_filter
                + " GROUP BY w.id ORDER BY COUNT(*) DESC,w.id LIMIT 12",
                (self.release, id),
            )
        ]
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
            contribution_total=total,
            next_cursor=self._next(offset, page_limit, total, signature),
            offset=offset,
            limit=page_limit,
            contributions=contributions,
            memberships=memberships,
            topics=[
                {k: t[k] for k in ("id", "title", "pillar")}
                for t in self.topic_metadata(work["topic_ids"])
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

    def _legacy_dossiers(self):
        from .coverage import assessed_route

        rows = []
        assessments = {
            r["topic"]: r for r in self.manifest.get("route_assessments", [])
        }
        # Decode subject records once, without loading every source and review.
        subject_records = [
            json.loads(row[0])
            for row in self.db.execute(
                "SELECT json_object('id',r.id,'revision',r.revision,'type',r.type,"
                "'content_hash',json_extract(r.payload,'$.content_hash'),"
                "'anchors',json_extract(r.payload,'$.anchors'),"
                "'limits',json_extract(r.payload,'$.limits'),"
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
                    "reading_route": assessed_route(
                        d, assessments.get(d["id"], {}), members, edges
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

    def brief(self, query, limit=12, policy=None, dossier=None):
        if dossier:
            try:
                assignment = self.dossier(dossier)["dossier"]
            except KeyError:
                raise ValueError("Unknown dossier") from None
            rows = self.db.execute(
                "SELECT n.id FROM topic_members t JOIN visible_nodes n ON n.snapshot=t.snapshot AND n.id=t.id WHERE t.snapshot=? AND t.topic=? ORDER BY n.id!=?,n.id LIMIT ?",
                (self.release, dossier, assignment.get("endpoint") or "", limit),
            ).fetchall()
            primary = self.get_many([r[0] for r in rows], "contribution")
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
                g for d in self.topic_metadata(dossiers) for g in d["gaps"]
            ],
            normative_sources_considered=[
                r["id"] for r in contributions if r["kind"] == "normative_argument"
            ],
            applicable_human_supplied_policy_profile=policy,
            permitted_action_scope="read_only",
            notice="This evidence brief is not authorization and does not establish expert validation.",
        )

    def changes(self, from_release, limit=None, offset=0):
        row = self.db.execute(
            "SELECT payload FROM snapshots WHERE id=?", (from_release,)
        ).fetchone()
        if not row:
            raise ValueError("Unknown comparison snapshot")
        prior_manifest = decode_snapshot(row[0])
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

        changes = {
            "from_release": from_release,
            "catalog_changes": catalog_changes,
            "added": [new[k] for k in sorted(new.keys() - old.keys())],
            "removed": [old[k] for k in sorted(old.keys() - new.keys())],
            "changed": [
                {"before": old[k], "after": new[k]}
                for k in sorted(new.keys() & old.keys())
                if old[k]["content_hash"] != new[k]["content_hash"]
            ],
        }
        if limit is not None:
            offset, limit, _ = self._page(
                offset, limit, None, ["changes", from_release]
            )
            # Read only identities/types for counting; decode full records only
            # for the requested page. Older clients can still request all refs.
            types = dict(
                self.db.execute(
                    "SELECT r.id, r.type FROM records r JOIN members m "
                    "ON r.id=m.id AND r.revision=m.revision WHERE m.snapshot IN (?,?)",
                    (from_release, self.release),
                )
            )
            counts, totals = {}, {}
            for kind in ("added", "removed", "changed"):
                typed = [
                    (item, types[(item["after"] if kind == "changed" else item)["id"]])
                    for item in changes[kind]
                ]
                counts[kind] = dict(Counter(record_type for _, record_type in typed))
                readable = [
                    item
                    for item, record_type in typed
                    if record_type in ("contribution", "relation")
                ]
                totals[kind] = len(readable)
                changes[kind] = readable[offset : offset + limit]
            changes.update(
                offset=offset, limit=limit, totals=totals, record_counts=counts
            )
        for kind in ("added", "removed"):
            changes[kind] = [describe(ref) for ref in changes[kind]]
        changes["changed"] = [
            {"before": describe(pair["before"]), "after": describe(pair["after"])}
            for pair in changes["changed"]
        ]
        return self.response(**changes)

    def info(self):
        return self._info

    def _calculate_info(self):
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
            tours=self.context.get("tours", []),
            maturity="exploratory",
            current_release_id=self.db.execute(
                "SELECT value FROM metadata WHERE key='current_release'"
            ).fetchone()[0],
            human_reviewed=human_reviewed,
        )
