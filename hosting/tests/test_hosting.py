"""Contract and access-boundary tests against the actual frozen reader database."""

from contextlib import closing
import json
import os
import shutil
import sqlite3
import re
from pathlib import Path
import sys
import tempfile
from urllib.parse import urlencode

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import HostedReader


@pytest.fixture(scope="module")
def app():
    source = Path(
        os.environ.get("TEST_BUNDLE", str(Path(__file__).resolve().parents[2]))
    )
    with tempfile.TemporaryDirectory(prefix="principia-hosting-test-") as temp:
        bundle = Path(temp)
        (bundle / "build").mkdir()
        if (source / "build/atlas.sqlite").exists():
            shutil.copyfile(
                source / "build/atlas.sqlite", bundle / "build/atlas.sqlite"
            )
        else:
            from principia_legacy.storage import build

            # Compile only in this disposable test home. The thin-client source
            # tree must not acquire a persistent database merely by running tests.
            for name in ("corpus", "manifests", "config", "tours"):
                (bundle / name).symlink_to(source / name, target_is_directory=True)
            build(bundle, "1.4.1-exploratory")
        with closing(
            sqlite3.connect(
                (bundle / "build/atlas.sqlite").resolve().as_uri() + "?mode=ro",
                uri=True,
            )
        ) as db:
            current = db.execute(
                "SELECT value FROM metadata WHERE key='current_release'"
            ).fetchone()[0]
            releases = [
                r[0]
                for r in db.execute("SELECT id FROM snapshots")
                if re.fullmatch(r"\d+\.\d+\.\d+-exploratory", r[0])
            ]
        # A local authoring database may activate "working". Hosting still selects
        # an explicitly published snapshot and must never expose that private view.
        default = (
            current
            if current in releases
            else max(
                releases,
                key=lambda value: tuple(map(int, value.split("-")[0].split("."))),
            )
        )
        config = {
            "default_release": default,
            "public_releases": releases,
            "hosts": ["atlas.example.org", "localhost", "127.0.0.1"],
        }
        (bundle / "hosting.json").write_text(json.dumps(config))
        yield HostedReader(bundle)


def request(
    app,
    path,
    params=None,
    method="GET",
    host="atlas.example.org",
    accept_encoding="identity",
):
    result = {}

    def start(status, headers):
        result["status"] = int(status.split()[0])
        result["headers"] = dict(headers)

    raw = b"".join(
        app(
            {
                "REQUEST_METHOD": method,
                "PATH_INFO": path,
                "QUERY_STRING": params
                if isinstance(params, str)
                else urlencode(params or {}),
                "HTTP_HOST": host,
                "HTTP_ACCEPT_ENCODING": accept_encoding,
            },
            start,
        )
    )
    result["raw"] = raw
    import gzip

    body = (
        gzip.decompress(raw)
        if raw and result["headers"].get("Content-Encoding") == "gzip"
        else raw
    )
    result["json"] = json.loads(body) if body else None
    return result


def test_pinned_release_and_info(app):
    result = request(app, "/api/info")
    assert result["status"] == 200
    info = result["json"]
    assert info["release_id"] == app.release
    assert info["current_release_id"] == app.release
    assert set(info["releases"]) == app.releases
    assert info["counts"]["contribution"] > 1000
    assert info["human_reviewed"] == 0
    assert result["headers"]["Content-Security-Policy"]


@pytest.mark.parametrize(
    "method", ["POST", "PUT", "PATCH", "DELETE", "OPTIONS", "TRACE", "CONNECT"]
)
def test_read_only(app, method):
    result = request(app, "/api/info", method=method)
    assert result["status"] == 405
    assert result["headers"]["Allow"] == "GET, HEAD"


@pytest.mark.parametrize(
    "host",
    ["evil.example", "atlas.example.org.evil.example", "atlas.example.org:99", ""],
)
def test_host_boundary(app, host):
    assert request(app, "/api/info", host=host)["status"] == 403


@pytest.mark.parametrize(
    "path", ["/api/info", "/api/search", "/api/brief", "/api/changes"]
)
def test_private_snapshot_denied(app, path):
    assert request(app, path, {"release": "working"})["status"] == 404


def test_private_comparison_denied(app):
    assert request(app, "/api/changes", {"from": "working"})["status"] == 400


def test_head_and_health(app):
    get = request(app, "/api/info")
    head = request(app, "/api/info", method="HEAD")
    assert head["raw"] == b""
    assert head["headers"]["Content-Length"] == str(len(get["raw"]))
    assert request(app, "/healthz")["json"]["release_id"] == app.release


def test_gzip_negotiation_and_head_use_the_same_representation(app):
    identity = request(app, "/api/dossiers")
    compressed = request(app, "/api/dossiers", accept_encoding="gzip")
    refused = request(app, "/api/dossiers", accept_encoding="gzip;q=0, identity;q=1")
    head = request(app, "/api/dossiers", method="HEAD", accept_encoding="gzip")
    assert compressed["headers"]["Content-Encoding"] == "gzip"
    assert compressed["headers"]["Vary"] == "Accept-Encoding"
    assert compressed["json"] == identity["json"] == refused["json"]
    assert "Content-Encoding" not in refused["headers"]
    assert len(compressed["raw"]) < len(identity["raw"])
    assert head["raw"] == b""
    assert head["headers"]["Content-Length"] == str(len(compressed["raw"]))


@pytest.mark.parametrize(
    "query",
    ["q=a&q=b", "q=" + "x" * 501, "limit=999999", "hops=7", "offset=-1", "limit=nan"],
)
def test_bounded_queries(app, query):
    assert request(app, "/api/search", query)["status"] == 400


def test_url_limit(app):
    assert request(app, "/api/search", "x=" + "a" * 8192)["status"] == 414


@pytest.mark.parametrize(
    "path",
    [
        "/.secrets/principia-legacy.env",
        "/build/atlas.sqlite",
        "/api/author",
        "/api/apply",
        "/api/contributions/missing",
    ],
)
def test_private_paths_unavailable(app, path):
    assert request(app, path)["status"] == 404


def test_query_and_release_cache_isolation(app):
    first = request(app, "/api/search", {"q": "entropy"})
    second = request(app, "/api/search", {"q": "Hamiltonian"})
    assert first["status"] == second["status"] == 200
    assert first["json"]["results"] != second["json"]["results"]
    for release in app.releases:
        out = request(app, "/api/info", {"release": release})
        assert out["json"]["release_id"] == release
    assert request(app, "/api/search", {"q": "entropy"})["raw"] == first["raw"]


def test_reader_workflows(app):
    result = request(app, "/api/search", {"q": "relativity"})["json"]
    node = result["results"][0]["id"]
    assert request(app, "/api/contributions/" + node)["status"] == 200
    assert request(app, "/api/neighborhood", {"seed": node})["status"] == 200
    assert request(app, "/api/dossiers")["status"] == 200
    assert request(app, "/api/brief", {"q": "relativity"})["status"] == 200
    if hasattr(app.Atlas, "people"):
        people = request(app, "/api/people", {"q": "Einstein"})
        assert people["status"] == 200
        entries = people["json"].get("people", people["json"].get("results", []))
        assert entries
        assert request(app, "/api/people/" + entries[0]["id"])["status"] == 200
    old = sorted(app.releases)[0]
    assert request(app, "/api/changes", {"from": old})["status"] == 200


def test_database_is_read_only(app):
    atlas = app.Atlas(app.root, app.release)
    try:
        with pytest.raises(Exception, match="readonly"):
            atlas.db.execute("DELETE FROM metadata")
    finally:
        atlas.close()


def test_cache_is_bounded(app):
    app = HostedReader(app.root)
    app.cache_budget = 1024
    for query in ("mechanics", "gravity", "quantum", "information"):
        assert request(app, "/api/search", {"q": query})["status"] == 200
    # A single item is permitted only if it fits the configured budget.
    assert app.cache_size <= app.cache_budget


def test_public_reader_uses_separate_pinned_data_home(app, tmp_path):
    config = {**app.config, "data_home": str(app.data_root)}
    (tmp_path / "hosting.json").write_text(json.dumps(config))
    hosted = HostedReader(tmp_path, atlas_class=app.Atlas)
    assert not (tmp_path / "build").exists()
    assert request(hosted, "/api/info")["json"]["release_id"] == app.release
    assert request(hosted, "/api/info", {"release": "working"})["status"] == 404


def test_public_changes_preserve_pagination_and_revision_pins(app):
    source = sorted(app.releases)[0]
    full = request(app, "/api/changes", {"from": source})["json"]
    page = request(app, "/api/changes", {"from": source, "limit": 1})["json"]
    second = request(app, "/api/changes", {"from": source, "limit": 1, "offset": 1})[
        "json"
    ]
    added = [r for r in full["added"] if r["type"] in ("contribution", "relation")]
    assert page["limit"] == 1
    assert page["totals"]["added"] == len(added)
    assert page["added"] + second["added"] == added[:2]
    assert page["snapshot_hash"] == full["snapshot_hash"] == second["snapshot_hash"]


def test_configured_semantic_index_must_match_public_release(app, monkeypatch):
    from principia_legacy import semantic

    monkeypatch.setenv("PRINCIPIA_SEMANTIC_HOME", "/configured/index")
    monkeypatch.setattr(semantic, "load", lambda atlas: None)
    with pytest.raises(ValueError, match="semantic index"):
        HostedReader(app.root)


def test_public_exploration_index_is_capped_read_only_and_snapshot_pinned(app):
    first = request(app, "/api/exploration-index", {"limit": 200})
    assert first["status"] == 200
    assert len(first["json"]["entries"]) == 200
    assert (
        first["json"]["total"]
        == request(app, "/api/info")["json"]["counts"]["contribution"]
    )
    assert first["json"]["release_id"] == app.release
    second = request(app, "/api/exploration-index", {"limit": 200, "offset": 200})
    assert first["json"]["snapshot_hash"] == second["json"]["snapshot_hash"]
    assert {e["id"] for e in first["json"]["entries"]}.isdisjoint(
        e["id"] for e in second["json"]["entries"]
    )
    assert request(app, "/api/exploration-index", {"limit": 201})["status"] == 400
    assert (
        request(app, "/api/exploration-index", {"release": "working"})["status"] == 404
    )
    assert request(app, "/api/exploration-index", method="POST")["status"] == 405
    csp = first["headers"]["Content-Security-Policy"]
    assert "https://api.siliconflow.cn" in csp
    assert "https://api.crossref.org" in csp
    assert "https://www.ebi.ac.uk" in csp
    assert "connect-src *" not in csp


def test_work_search_detail_and_subjects(app):
    info = request(app, "/api/info")["json"]
    if not info.get("catalog_counts", {}).get("works"):
        pytest.skip("External test bundle predates the work catalogue")
    result = request(app, "/api/search", {"q": "Allan Turing"})["json"]
    assert any(p["name"] == "Alan Turing" for p in result["people"])
    assert result["works"]
    work = request(app, "/api/works/" + result["works"][0]["id"])
    assert work["status"] == 200
    assert work["json"]["release_id"] == app.release
    assert work["json"]["sources"] and work["json"]["contributions"]
    assert request(app, "/api/works", {"topic": "C1002"})["json"]["works"]
    people = request(app, "/api/people", {"pillar": "physics"})["json"]["people"]
    assert people and all("physics" in p["subjects"] for p in people)
    assert request(app, "/api/works", method="POST")["status"] == 405
