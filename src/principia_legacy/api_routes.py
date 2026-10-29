"""Shared additive collection routes for local and hosted readers."""

from urllib.parse import unquote

from . import exploration_index


def collection_route(atlas, path, q):
    if path == "/api/coverage":
        return atlas.coverage_summary()
    if path == "/api/exploration-manifest":
        return exploration_index.manifest(atlas)
    if path == "/api/exploration-shard":
        return exploration_index.shard(atlas, q.get("shard", ""))
    if path == "/api/exploration-records":
        return exploration_index.records(atlas, q.get("ids", ""))
    if path == "/api/topic-overview":
        return atlas.topic_overview()
    if path == "/api/dossiers":
        return atlas.dossiers(
            q.get("limit"),
            q.get("offset", 0),
            q.get("pillar"),
            q.get("area"),
            q.get("status"),
            q.get("q", ""),
            q.get("cursor"),
            q.get("summary") == "true",
        )
    if path.startswith("/api/dossiers/"):
        parts = path.split("/")
        id = unquote(parts[3])
        if len(parts) == 5 and parts[4] == "contributions":
            return atlas.topic_contributions(
                id,
                q.get("limit", 40),
                q.get("offset", 0),
                q.get("human") == "true",
                q.get("cursor"),
            )
        if len(parts) == 4:
            return atlas.dossier(id)
        raise KeyError("Unknown topic route")
    if path.startswith("/api/people/"):
        return atlas.person(
            unquote(path.rsplit("/", 1)[1]),
            q.get("human") == "true",
            q.get("limit", 40),
            q.get("offset", 0),
            q.get("cursor"),
        )
    if path.startswith("/api/works/"):
        return atlas.work(
            unquote(path.rsplit("/", 1)[1]),
            q.get("human") == "true",
            q.get("limit", 40),
            q.get("offset", 0),
            q.get("cursor"),
        )
    if q.get("cursor"):
        if path == "/api/search":
            return atlas.search(
                q.get("q", ""),
                q.get("pillar"),
                q.get("human") == "true",
                q.get("limit", 40),
                cursor=q["cursor"],
            )
        if path == "/api/people":
            return atlas.people(
                q.get("q", ""),
                q.get("limit", 60),
                human=q.get("human") == "true",
                pillar=q.get("pillar"),
                cursor=q["cursor"],
            )
        if path == "/api/works":
            return atlas.works(
                q.get("q", ""),
                q.get("pillar"),
                q.get("topic"),
                q.get("person"),
                q.get("human") == "true",
                q.get("limit", 40),
                cursor=q["cursor"],
            )
    return None
