"""Build-time projections. Canonical records and frozen manifests stay authoritative."""

import json
from collections import defaultdict, deque
from .records import visible


def install(db):
    db.executescript("""
    CREATE TABLE visible_nodes(snapshot TEXT,id TEXT,revision INTEGER,pillar TEXT,human TEXT,title TEXT,year INTEGER,PRIMARY KEY(snapshot,id));
    CREATE INDEX visible_subject ON visible_nodes(snapshot,pillar,id);
    CREATE INDEX visible_human ON visible_nodes(snapshot,human,id);
    CREATE TABLE catalog_subjects(snapshot TEXT,kind TEXT,id TEXT,pillar TEXT,PRIMARY KEY(snapshot,kind,pillar,id));
    CREATE INDEX catalog_subject_id ON catalog_subjects(snapshot,kind,id);
    CREATE INDEX work_people_person ON work_people(snapshot,person,work);
    CREATE INDEX work_topic_work ON work_topics(snapshot,work,topic);
    CREATE INDEX work_link_from ON work_links(snapshot,json_extract(payload,'$.from.id'));
    CREATE INDEX work_link_to ON work_links(snapshot,json_extract(payload,'$.to.id'));
    CREATE TABLE topic_summaries(snapshot TEXT,id TEXT,title TEXT,pillar TEXT,area TEXT,status TEXT,populated INTEGER,payload TEXT,PRIMARY KEY(snapshot,id));
    CREATE INDEX topic_filter ON topic_summaries(snapshot,pillar,status,id);
    CREATE TABLE snapshot_context(snapshot TEXT PRIMARY KEY,hash TEXT,payload TEXT,info TEXT);
    CREATE TABLE topic_evidence(snapshot TEXT,topic TEXT,id TEXT,payload TEXT,PRIMARY KEY(snapshot,topic,id));
    CREATE TABLE topic_positions(snapshot TEXT,topic TEXT,id TEXT,position INTEGER,PRIMARY KEY(snapshot,topic,id));
    CREATE INDEX topic_position ON topic_positions(snapshot,topic,position);
    """)


def populate(db, manifest, records, people, works):
    snapshot = manifest["release_id"]
    db.executemany(
        "INSERT INTO topic_evidence VALUES(?,?,?,?)",
        (
            (
                snapshot,
                m["topic_id"],
                m["contribution"]["id"],
                json.dumps(m, ensure_ascii=False),
            )
            for m in manifest.get("topic_memberships", [])
        ),
    )
    human = {}
    for r in records:
        if r["type"] == "review" and r["reviewer_type"] == "human":
            key = r["target"]["content_hash"]
            if r["judgment"] in ("disputed", "rejected"):
                human[key] = "disputed"
            elif r["judgment"] == "accepted" and human.get(key) != "disputed":
                human[key] = (
                    "domain_expert"
                    if r["scope"] == "domain_expert"
                    or human.get(key) == "domain_expert"
                    else "editorial"
                )
    db.executemany(
        "INSERT INTO visible_nodes VALUES(?,?,?,?,?,?,?)",
        (
            (
                snapshot,
                r["id"],
                r["revision"],
                r["pillar"],
                human.get(r["content_hash"], "not_reviewed"),
                r["title"],
                r["date"]["year"],
            )
            for r in records
            if r["type"] == "contribution" and visible(r)
        ),
    )
    db.executemany(
        "INSERT INTO catalog_subjects VALUES(?,?,?,?)",
        (
            (snapshot, kind, r["id"], subject)
            for kind, rows in [("person", people.values()), ("work", works.values())]
            for r in rows
            for subject in set(r.get("subjects", []))
        ),
    )


def summarize(db, manifest, rows):
    db.executemany(
        "INSERT INTO topic_summaries VALUES(?,?,?,?,?,?,?,?)",
        (
            (
                manifest["release_id"],
                d["id"],
                d["title"],
                d["pillar"],
                d.get("area", ""),
                d["status"],
                int(d["contribution_count"] > 0),
                json.dumps(d, ensure_ascii=False),
            )
            for d in rows
        ),
    )


def rank_topics(db, manifest):
    """Stable, bounded runtime neighborhoods; compute whole-topic distance once."""
    snapshot = manifest["release_id"]
    members, owners = defaultdict(set), defaultdict(set)
    for topic, id in db.execute(
        "SELECT topic,id FROM topic_members WHERE snapshot=?", (snapshot,)
    ):
        members[topic].add(id)
        owners[id].add(topic)
    relations = defaultdict(set)
    for relation, endpoint in db.execute(
        "SELECT relation_id,endpoint_id FROM adjacency WHERE snapshot=?", (snapshot,)
    ):
        relations[relation].add(endpoint)
    neighbors = {topic: defaultdict(set) for topic in members}
    for endpoints in relations.values():
        topics = (
            set.intersection(*(owners[id] for id in endpoints)) if endpoints else set()
        )
        for topic in topics:
            for id in endpoints:
                neighbors[topic][id].update(endpoints - {id})
    for topic in manifest["dossiers"]:
        id, endpoint = topic["id"], topic.get("endpoint")
        distances = {endpoint: 0} if endpoint in members[id] else {}
        queue = deque(distances)
        while queue:
            node = queue.popleft()
            for next_id in neighbors.get(id, {}).get(node, ()):
                if next_id not in distances:
                    distances[next_id] = distances[node] + 1
                    queue.append(next_id)
        ordered = sorted(
            members[id],
            key=lambda node: (
                distances.get(node, float("inf")),
                -len(neighbors.get(id, {}).get(node, ())),
                node,
            ),
        )
        db.executemany(
            "INSERT INTO topic_positions VALUES(?,?,?,?)",
            ((snapshot, id, node, position) for position, node in enumerate(ordered)),
        )
