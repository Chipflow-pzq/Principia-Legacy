"""Compact public discovery shards. Personal questions never enter these APIs."""

import json
from .common import digest


def install(db):
    db.executescript("""
    CREATE TABLE exploration_shards(snapshot TEXT,id TEXT,pillar TEXT,total INTEGER,hash TEXT,payload TEXT,PRIMARY KEY(snapshot,id));
    """)


def compile_shards(db, snapshot):
    neighbors = {}
    for relation, endpoint in db.execute(
        "SELECT relation_id,endpoint_id FROM adjacency WHERE snapshot=? ORDER BY relation_id",
        (snapshot,),
    ):
        neighbors.setdefault(relation, []).append(endpoint)
    adjacent = {}
    for endpoints in neighbors.values():
        for node in endpoints:
            adjacent.setdefault(node, set()).update(set(endpoints) - {node})
    for (pillar,) in db.execute(
        "SELECT DISTINCT pillar FROM visible_nodes WHERE snapshot=? ORDER BY pillar",
        (snapshot,),
    ).fetchall():
        rows = db.execute(
            "SELECT r.payload FROM visible_nodes n JOIN records r ON r.id=n.id AND r.revision=n.revision WHERE n.snapshot=? AND n.pillar=? ORDER BY n.id",
            (snapshot, pillar),
        )
        entries, part = [], 0

        def save():
            payload = json.dumps(entries, ensure_ascii=False, separators=(",", ":"))
            db.execute(
                "INSERT INTO exploration_shards VALUES(?,?,?,?,?,?)",
                (
                    snapshot,
                    f"{pillar}-{part}",
                    pillar,
                    len(entries),
                    digest(payload.encode()),
                    payload,
                ),
            )

        for (payload,) in rows:
            n = json.loads(payload)
            entries.append(
                {
                    k: n[k]
                    for k in (
                        "id",
                        "revision",
                        "content_hash",
                        "title",
                        "kind",
                        "pillar",
                        "date",
                    )
                }
                | {
                    "attribution": [
                        {k: a[k] for k in ("name", "role")} for a in n["attribution"]
                    ],
                    "claim": n["claim"][:600],
                    "explanation": "",
                    "limits": [],
                    "assumptions": [],
                    "neighbors": sorted(adjacent.get(n["id"], []))[:32],
                    "compact": True,
                }
            )
            if len(entries) == 500:
                save()
                entries = []
                part += 1
        if entries:
            save()


def manifest(atlas):
    shards = [
        dict(zip(("id", "pillar", "total", "hash"), r))
        for r in atlas.db.execute(
            "SELECT id,pillar,total,hash FROM exploration_shards WHERE snapshot=? ORDER BY id",
            (atlas.release,),
        )
    ]
    return atlas.response(
        format="principia-search-shards/v1",
        shards=shards,
        total=sum(s["total"] for s in shards),
    )


def shard(atlas, id):
    row = atlas.db.execute(
        "SELECT hash,payload FROM exploration_shards WHERE snapshot=? AND id=?",
        (atlas.release, id),
    ).fetchone()
    if not row:
        raise KeyError(id)
    return atlas.response(hash=row[0], payload=row[1])


def records(atlas, ids):
    ids = ids.split(",") if isinstance(ids, str) else ids
    if not ids or len(ids) > 40 or any(len(id) > 160 for id in ids):
        raise ValueError("Select between one and forty public records")
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
    from .records import visible

    values = [r for r in atlas.get_many(ids, "contribution") if visible(r)]
    return atlas.response(entries=[{k: r[k] for k in fields} for r in values])
