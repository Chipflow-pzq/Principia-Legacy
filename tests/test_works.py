# ruff: noqa: F811
import copy
from contextlib import closing

import pytest
from test_catalog import add_navigation
from test_core import atlas_root, records  # noqa: F401

from principia_legacy.common import digest, read_json, seal, write_json, write_lines
from principia_legacy.lifecycle import apply_patch, impact, prepare_patch
from principia_legacy.release import freeze
from principia_legacy.retrieval import distance
from principia_legacy.storage import Atlas, build


def add_works(root):
    add_navigation(root)
    people = read_json(root / "manifests/people.json")
    people[0]["selection_reason"] = "Fixture selection"
    people[0]["aliases"].extend(["Alan Turing", "John von Neumann", "Emmanuel Candès"])
    write_json(root / "manifests/people.json", people)
    source, n = records()[:2]
    ref = lambda r: {k: r[k] for k in ["id", "revision", "content_hash"]}
    work = {
        "id": "w1",
        "revision": 1,
        "title": "Universal computing machines",
        "kind": "paper",
        "subjects": ["mathematics", "computer_science"],
        "summary": "A computation work",
        "people": ["person-test"],
        "topic_ids": ["M01", "C01"],
        "source_refs": [ref(source)],
        "provenance": people[0]["bio_sources"],
    }
    work["content_hash"] = digest(work)
    other = {**work, "id": "w2", "title": "Another account", "content_hash": ""}
    other["content_hash"] = digest(
        {k: v for k, v in other.items() if k != "content_hash"}
    )
    write_json(root / "manifests/works.json", [work, other])
    write_json(
        root / "manifests/work_insights.json",
        [
            {
                "work_id": id,
                "contribution": ref(n),
                "role": "explains",
                "reason": "Explicit fixture passage mapping",
                "anchors": n["anchors"],
            }
            for id in ["w1", "w2"]
        ],
    )
    write_json(
        root / "config/search_concepts.json",
        [{"terms": ["universal computation", "universal computing", "computability"]}],
    )
    build(root)


def test_four_search_categories_and_many_to_many_navigation(atlas_root):
    add_works(atlas_root)
    with closing(Atlas(atlas_root)) as a:
        assert a.search("computability")["works"][0]["id"] == "w1"
        assert a.search("von neuman")["people"][0]["id"] == "person-test"
        assert a.search("turrng")["people"][0]["id"] == "person-test"
        assert a.search("Candes")["people"][0]["id"] == "person-test"
        assert set(a.search("finite")["totals"]) == {
            "ideas",
            "topics",
            "people",
            "works",
        }
        assert len(a.inspect("n1", "contribution")["works"]) == 2
        w = a.work("w1")
        assert len(w["topics"]) == 2 and len(w["contributions"]) == 1
        assert w["shared_insights"][0]["work"]["id"] == "w2"
        assert len(a.works(topic="C01")["works"]) == 2
        assert len(a.person("person-test")["works"]) == 2
        assert a.works(human=True)["total"] == 0
        assert a.people(pillar="physics")["total"] == 0
        assert a.info()["catalog_counts"]["works"] == 2
        brief = a.brief("finite")
        assert len(brief["works"]) == 2 and brief["sources"][0]["id"] == "s1"
        assert impact(atlas_root, "n1")["affected_works"] == ["w1", "w2"]


def test_changed_claim_drops_work_interpretation_preserves_snapshot(atlas_root):
    add_works(atlas_root)
    freeze(atlas_root, "work-before")
    rs = records()
    n = copy.deepcopy(rs[1])
    n.update(revision=2, claim="Changed finite claim", publication_state="candidate")
    seal(n)
    patch = prepare_patch(
        atlas_root,
        {
            "reason": "Correct fixture",
            "base_hashes": {"n1": rs[1]["content_hash"]},
            "records": [n],
        },
    )
    write_json(atlas_root / "patch.json", patch)
    apply_patch(atlas_root, atlas_root / "patch.json")
    build(atlas_root)
    with closing(Atlas(atlas_root)) as a:
        assert a.work("w1")["contributions"] == []
        assert a.work("w1")["work"]["status"] == "catalogued"
    with closing(Atlas(atlas_root, "work-before")) as a:
        assert len(a.work("w1")["contributions"]) == 1


def test_catalog_does_not_create_people_from_credit_strings(atlas_root):
    add_works(atlas_root)
    rs = records()
    rs[1]["attribution"] = [
        {
            "name": "Anastasios Angelopoulos, Stephen Bates, Emmanuel Candès, Michael Jordan, Lihua Lei",
            "role": "authors",
        }
    ]
    write_lines(atlas_root / "corpus/records.jsonl", [seal(r) for r in rs])
    # The changed contribution hash deliberately invalidates its work membership.
    build(atlas_root)
    with closing(Atlas(atlas_root)) as a:
        assert a.people()["total"] == 1
        assert not a.search("Angelopoulos")["people"]
        assert not a.inspect("n1", "contribution")["people"]


def test_work_validation_rejects_hash_anchor_and_identity_errors(atlas_root):
    add_works(atlas_root)
    works = read_json(atlas_root / "manifests/works.json")
    works[0]["title"] = "tampered"
    write_json(atlas_root / "manifests/works.json", works)
    with pytest.raises(ValueError, match="hash mismatch"):
        build(atlas_root)
    works[0]["content_hash"] = digest(
        {k: v for k, v in works[0].items() if k != "content_hash"}
    )
    works[0]["people"] = ["unknown"]
    works[0]["content_hash"] = digest(
        {k: v for k, v in works[0].items() if k != "content_hash"}
    )
    write_json(atlas_root / "manifests/works.json", works)
    with pytest.raises(ValueError, match="undefined individual"):
        build(atlas_root)


def test_typo_distance_is_bounded_and_transpositions_work():
    assert distance("turing", "tuirng") == 1
    assert distance("neumann", "neuman") == 1
    assert distance("quantum", "quantom") == 1
    assert distance("math", "biology") > 2


def test_metadata_revision_invalidates_membership_and_old_catalog_survives(atlas_root):
    add_works(atlas_root)
    from principia_legacy.storage import manifest
    from principia_legacy.works import compile_works

    m = manifest(atlas_root)
    for member in m["work_insights"]:
        work = next(w for w in m["works"] if w["id"] == member["work_id"])
        member["work"] = {k: work[k] for k in ("id", "revision", "content_hash")}
    m["works"][0]["revision"] += 1
    m["works"][0]["summary"] = "Corrected scope"
    m["works"][0]["content_hash"] = digest(
        {k: v for k, v in m["works"][0].items() if k != "content_hash"}
    )
    nodes = {n["id"]: n for n in records() if n["type"] == "contribution"}
    _, memberships, _ = compile_works(m, nodes, records())
    assert ("w1", "n1") not in memberships and ("w2", "n1") in memberships


def test_source_enrichment_keeps_membership_but_changed_evidence_drops_it(atlas_root):
    add_works(atlas_root)
    from principia_legacy.storage import manifest
    from principia_legacy.works import compile_works

    m = manifest(atlas_root)
    source = copy.deepcopy(records()[0])
    source["revision"] = 2
    source["anchors"].append(
        {
            "id": "a2",
            "selector": "Appendix",
            "summary": "More evidence",
            "checked": True,
        }
    )
    seal(source)
    m["record_refs"] = [
        {k: source[k] for k in ("id", "revision", "content_hash")}
        if r["id"] == "s1"
        else r
        for r in m["record_refs"]
    ]
    nodes = {n["id"]: n for n in records() if n["type"] == "contribution"}
    assert len(compile_works(m, nodes, [*records(), source])[1]) == 2
    source["anchors"][0]["summary"] = "Revised evidence"
    seal(source)
    assert not compile_works(m, nodes, [*records(), source])[1]


def test_work_connections_cannot_flatten_joint_premises_or_inherit_stale_checks(
    atlas_root,
):
    add_works(atlas_root)
    from principia_legacy.storage import manifest
    from principia_legacy.works import compile_works

    m = manifest(atlas_root)
    ref = lambda r: {k: r[k] for k in ("id", "revision", "content_hash")}
    edge = records()[-1]
    link = {
        "id": "wl1",
        "revision": 1,
        "from": ref(m["works"][0]),
        "to": ref(m["works"][1]),
        "basis_relation": ref(edge),
        "predicate": edge["predicate"],
        "warrant": edge["warrant"],
        "provenance": m["works"][0]["provenance"],
    }
    link["content_hash"] = digest(link)
    m["work_relations"] = [link]
    nodes = {n["id"]: n for n in records() if n["type"] == "contribution"}
    with pytest.raises(ValueError, match="joint premises"):
        compile_works(m, nodes, records())
    link["basis_relation"]["revision"] = 99
    link["content_hash"] = digest(
        {k: v for k, v in link.items() if k != "content_hash"}
    )
    assert not compile_works(m, nodes, records())[2]
    link.pop("basis_relation")
    link["content_hash"] = digest(
        {k: v for k, v in link.items() if k != "content_hash"}
    )
    with pytest.raises(ValueError, match="checked insight"):
        compile_works(m, nodes, records())


def test_search_is_bounded_and_never_interprets_sql_or_query_instructions(atlas_root):
    add_works(atlas_root)
    with closing(Atlas(atlas_root)) as a:
        assert a.search("what is computability")["works"]
        assert not a.search("'; DROP TABLE works; --")["works"]
        assert a.works()["total"] == 2
        assert a.search("computability", limit=10000)["limit"] == 100
        with pytest.raises(ValueError, match="too long"):
            a.search("a" * 501)
        assert not a.work("w1", human=True)["shared_insights"]
        assert not a.work("w1", human=True)["relations"]
        assert a.search("Alan Turing")["works"]


def test_work_http_routes_are_read_only_and_release_pinned(atlas_root):
    import json
    import threading
    from http.server import ThreadingHTTPServer
    from urllib.error import HTTPError
    from urllib.request import Request, urlopen

    from principia_legacy.serve import handler_for

    add_works(atlas_root)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(atlas_root))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = "http://127.0.0.1:" + str(server.server_port)
    try:
        for path in ("/api/works", "/api/works/w1", "/api/search?q=computability"):
            with urlopen(base + path) as r:
                result = json.load(r)
                assert result["release_id"] == "working" and result["snapshot_hash"]
        with pytest.raises(HTTPError) as e:
            urlopen(Request(base + "/api/works/w1", data=b"{}", method="POST"))
        assert e.value.code == 405
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
