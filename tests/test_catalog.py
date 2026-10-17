# ruff: noqa: F811 -- pytest fixture imported from shared corpus
import copy
from contextlib import closing
import pytest
from test_core import atlas_root, records  # noqa: F401
from principia_legacy.catalog import navigation_index, contributor_id
from principia_legacy.common import read_json, read_lines, write_lines, write_json, seal
from principia_legacy.storage import Atlas, build, manifest
from principia_legacy.release import freeze
from principia_legacy.lifecycle import prepare_patch, apply_patch, impact


def add_navigation(root):
    topic = copy.deepcopy(read_lines(root / "manifests/FRONTIER_REGISTRY.jsonl")[0])
    topic.update(
        id="C01", title="A cross-subject application", pillar="computer_science"
    )
    write_lines(
        root / "manifests/FRONTIER_REGISTRY.jsonl",
        [*read_lines(root / "manifests/FRONTIER_REGISTRY.jsonl"), topic],
    )
    n = records()[1]
    write_json(
        root / "manifests/topic_memberships.json",
        [
            {
                "topic_id": "C01",
                "contribution": {k: n[k] for k in ("id", "revision", "content_hash")},
                "reason": "Read the finite result in a computational setting; this is not an influence assertion.",
            }
        ],
    )
    write_json(
        root / "manifests/people.json",
        [
            {
                "id": "person-test",
                "name": "Test author",
                "aliases": ["T. Author"],
                "kind": "person",
                "biography": "Author of the finite-scope fixture.",
                "bio_sources": [
                    {
                        "url": "https://example.org/paper",
                        "title": "Test source",
                        "note": "Fixture author attribution.",
                    }
                ],
            }
        ],
    )
    build(root)


def test_topic_links_search_profiles_and_brief(atlas_root):
    add_navigation(atlas_root)
    with closing(Atlas(atlas_root)) as a:
        inspected = a.inspect("n1", "contribution")
        assert {t["id"] for t in inspected["topics"]} == {"M01", "C01"}
        assert inspected["people"][0]["id"] == "person-test"
        assert len(a.person("person-test")["contributions"]) == 3
        assert {t["id"] for t in a.person("person-test")["topics"]} == {"M01", "C01"}
        assert a.search("T. Author")["people"][0]["name"] == "Test author"
        assert a.search("cross-subject")["topics"][0]["id"] == "C01"
        assert (
            a.search("finite", limit=1, offset=1)["results"][0]["id"]
            != a.search("finite", limit=1)["results"][0]["id"]
        )
        assert a.search('" OR *')["totals"]["ideas"] == 0
        assert a.brief("", dossier="C01")["relevant_contributions"][0]["id"] == "n1"
        assert (
            next(t for t in a.dossiers()["dossiers"] if t["id"] == "C01")[
                "contribution_count"
            ]
            == 1
        )
        assert sum(a.info()["subject_counts"].values()) == 3
        with pytest.raises(ValueError):
            a.people("x" * 501)


def test_alias_safety_and_ambiguity(atlas_root):
    add_navigation(atlas_root)
    m = manifest(atlas_root)
    m["people"].append({**m["people"][0], "id": "other"})
    with pytest.raises(ValueError, match="Ambiguous"):
        navigation_index(m, records())
    m = manifest(atlas_root)
    m["people"][0]["bio_sources"][0]["url"] = "javascript:alert(1)"
    with pytest.raises(ValueError, match="HTTPS"):
        navigation_index(m, records())
    m = manifest(atlas_root)
    m["people"][0]["bio_sources"] = []
    with pytest.raises(ValueError, match="sources"):
        navigation_index(m, records())


def test_shared_membership_invalidated_on_revision_and_old_snapshot_kept(atlas_root):
    add_navigation(atlas_root)
    freeze(atlas_root, "navigation-before")
    rows = records()
    changed = copy.deepcopy(rows[1])
    changed["revision"] = 2
    changed["claim"] = "A corrected finite result"
    seal(changed)
    # Candidate revisions stay outside browsing, invalidating shared navigation.
    changed["publication_state"] = "candidate"
    seal(changed)
    assert "C01" in impact(atlas_root, "n1")["affected_dossiers"]
    patch = prepare_patch(
        atlas_root,
        {
            "reason": "Test scoped correction",
            "base_hashes": {"n1": rows[1]["content_hash"]},
            "records": [changed],
        },
    )
    write_json(atlas_root / "correction.json", patch)
    apply_patch(atlas_root, atlas_root / "correction.json")
    build(atlas_root)
    with closing(Atlas(atlas_root)) as a:
        assert not a.topics_for("n1")
    with closing(Atlas(atlas_root, "navigation-before")) as a:
        assert len(a.topics_for("n1")) == 2
        assert a.person("person-test")["person"]["name"] == "Test author"


def test_group_credit_requires_source_match(atlas_root):
    add_navigation(atlas_root)
    m = manifest(atlas_root)
    r = records()
    r[1]["attribution"][0]["name"] = "Team et al."
    m["credit_groups"] = [
        {"credit": "Team et al.", "people": ["person-test"], "source_ids": ["s-other"]}
    ]
    _, _, _people, links = navigation_index(m, r)
    assert (contributor_id("Team et al."), "n1") in links
    m["credit_groups"][0]["source_ids"] = ["s1"]
    _, _, _people, links = navigation_index(m, r)
    assert ("person-test", "n1") in links
    assert links[("person-test", "n1")]["recorded_name"] == "Team et al."


def test_internal_checkpoint_restores_without_multiplying_default_indexes(atlas_root):
    freeze(atlas_root, "before-test-checkpoint")
    build(atlas_root)
    with closing(Atlas(atlas_root)) as a:
        assert "before-test-checkpoint" not in a.info()["releases"]
    build(atlas_root, "before-test-checkpoint")
    with closing(Atlas(atlas_root)) as a:
        assert a.release == "before-test-checkpoint"
        assert a.get("n1")["claim"] == "A finite result"


def test_publisher_math_and_article_scope_are_preserved():
    from principia_legacy.acquire import ArticleParser

    p = ArticleParser(book_content_only=True)
    p.feed(
        '<title>Article title</title><div>Irrelevant navigation that must not be extracted.</div><div data-book-content="true"><p>A mathematical result with an exponent <math><msup><mi>x</mi><mn>2</mn></msup></math> and its assumptions.</p></div><p>Unrelated marketing must not become source evidence.</p>'
    )
    assert len(p.lines) == 1
    assert "<msup><mi>x</mi><mn>2</mn></msup>" in p.lines[0]
    assert "marketing" not in p.lines[0]


def test_people_human_filter_does_not_imply_unperformed_review(atlas_root):
    add_navigation(atlas_root)
    build(atlas_root)
    with closing(Atlas(atlas_root)) as a:
        assert a.people()["total"] > 0
        assert a.people(human=True)["total"] == 0
        assert not a.person("person-test", human=True)["contributions"]


def test_shared_membership_evidence_survives_inspection_and_export(atlas_root):
    add_navigation(atlas_root)
    path = atlas_root / "manifests/topic_memberships.json"
    memberships = read_json(path)
    memberships[0].update(
        anchors=[{"source_id": "s1", "source_revision": 1, "anchor_id": "a1"}],
        screening_request_id="fixture-request",
    )
    write_json(path, memberships)
    build(atlas_root)
    with closing(Atlas(atlas_root)) as a:
        inspected = a.inspect("n1", "contribution")
        assert inspected["navigation_source_anchors"][0]["anchor_id"] == "a1"
        brief = a.brief("", dossier="C01")
        assert brief["navigation_source_anchors"]
        assert {s["id"] for s in brief["sources"]} == {"s1"}
        assert brief["topic_memberships"][0]["contribution"]["content_hash"]
    memberships[0]["anchors"][0]["anchor_id"] = "missing"
    write_json(path, memberships)
    with pytest.raises(ValueError, match="unresolved source anchor"):
        build(atlas_root)


def test_reuse_needs_exact_independent_decisions_and_passages():
    from principia_legacy.curate import checked_reuse

    n = records()[1]
    reuse = [
        {
            "id": "n1",
            "reason": "Explains this topic under the same finite scope.",
            "passage_ids": ["p1"],
        }
    ]
    checked = {
        "source_relevant": True,
        "reuse": [
            {
                "index": 0,
                "decision": "supported",
                "rationale": "The exact move is explained.",
            }
        ],
    }
    assert checked_reuse(reuse, {"n1": n}, checked, [{"id": "p1"}]) == reuse
    assert checked_reuse(reuse, {"n1": n}, checked, [{"id": "p2"}]) == []
    assert checked_reuse(reuse, {}, checked, [{"id": "p1"}]) == []
    checked["source_relevant"] = False
    assert checked_reuse(reuse, {"n1": n}, checked, [{"id": "p1"}]) == []
    with pytest.raises(ValueError, match="Incomplete"):
        checked_reuse(reuse, {"n1": n}, {"source_relevant": True}, [{"id": "p1"}])


def test_reuse_admission_keeps_one_identity_and_source_corrections_invalidate_route(
    atlas_root, monkeypatch
):
    from principia_legacy import curate, expansion

    add_navigation(atlas_root)
    (atlas_root / "prompts").mkdir()
    for name in ("extract.txt", "check.txt"):
        (atlas_root / "prompts" / name).write_text("Fixture-only provider contract")
    # Start without the manually added membership so the complete authoring path
    # must establish the route and its independently checked evidence.
    write_json(atlas_root / "manifests/topic_memberships.json", [])
    source_url = "https://example.org/second-exposition"
    source = dict(
        title="Second exposition",
        creators=["Test author"],
        date="2020",
        resolved_url=source_url,
        bytes_hash="source-v2",
        retrieved_at="2026-10-13",
        passages=[
            {
                "id": "p1",
                "selector": "Section 1",
                "text": "The same finite-scope theorem explains the computational topic.",
            }
        ],
    )
    monkeypatch.setattr(curate, "acquire", lambda *args: source)
    monkeypatch.setattr(
        expansion, "candidate_reuse_hints", lambda *args: [records()[1]]
    )
    calls = []

    class FixtureProvider:
        def __init__(self, *args):
            pass

        def complete(self, system, payload, task, *args):
            calls.append(task)
            receipt = {"request_id": task, "requested_model": "fixture-only"}
            if task.startswith("extract:"):
                return {
                    "relevant": True,
                    "contributions": [
                        {"title": "Finite theorem", "claim": "A finite result"}
                    ],
                }, receipt
            if task.startswith("reuse-refinement:"):
                return {
                    "relevant": True,
                    "contributions": [],
                    "relations": [],
                    "reuse": [
                        {
                            "id": "n1",
                            "reason": "The same finite theorem explains the computational setting.",
                            "passage_ids": ["p1"],
                        }
                    ],
                }, receipt
            return {
                "source_relevant": True,
                "contributions": [],
                "relations": [],
                "reuse": [
                    {
                        "index": 0,
                        "decision": "supported",
                        "rationale": "The exact same move is explained under the same attribution and scope.",
                    }
                ],
            }, receipt

    monkeypatch.setattr(curate, "Provider", FixtureProvider)
    topic = next(
        d
        for d in read_lines(atlas_root / "manifests/FRONTIER_REGISTRY.jsonl")
        if d["id"] == "C01"
    )
    result = curate.process_source(atlas_root, topic, source_url)
    assert len(calls) == 3
    assert result["reuse_refinement"]["accepted_memberships"] == 1
    assert not any(r["type"] == "contribution" for r in result["records"])
    expansion.admit(
        atlas_root,
        {"id": "reuse-fixture"},
        [{"state": "succeeded", "dossier": "C01", "result": result}],
    )
    freeze(atlas_root, "reuse-before-source-correction")
    build(atlas_root)
    with closing(Atlas(atlas_root)) as a:
        assert a.info()["counts"]["contribution"] == 3
        assert len(a.topics_for("n1")) == 2
        assert len(a.inspect("n1", "contribution")["sources"]) == 2
        assert len(a.brief("", dossier="C01")["sources"]) == 2
    changed = copy.deepcopy(result["records"][0])
    assert "C01" in impact(atlas_root, changed["id"])["affected_dossiers"]
    changed["revision"] += 1
    changed["title"] = "Corrected source description"
    seal(changed)
    write_lines(atlas_root / "corpus/source-correction.jsonl", [changed])
    build(atlas_root)
    with closing(Atlas(atlas_root)) as a:
        assert len(a.topics_for("n1")) == 1
    with closing(Atlas(atlas_root, "reuse-before-source-correction")) as a:
        assert len(a.topics_for("n1")) == 2


def test_checked_reuse_can_be_a_relation_endpoint_at_its_actual_revision(
    atlas_root, monkeypatch
):
    from principia_legacy import curate

    existing = copy.deepcopy(records()[1])
    existing.update(revision=2, claim="A corrected finite result")
    seal(existing)
    write_lines(atlas_root / "corpus/correction.jsonl", [existing])
    (atlas_root / "prompts").mkdir()
    for name in ("extract.txt", "check.txt"):
        (atlas_root / "prompts" / name).write_text("Fixture contract")
    passage = {
        "id": "p1",
        "selector": "Section 1",
        "text": "The corrected finite result entails a distinct application under the stated conditions.",
    }
    monkeypatch.setattr(
        curate,
        "acquire",
        lambda *args: {
            "title": "Application",
            "creators": ["Test author"],
            "date": "2020",
            "resolved_url": "https://example.org/application",
            "bytes_hash": "fixture-v1",
            "retrieved_at": "2026-10-17",
            "passages": [passage],
        },
    )
    candidate = {
        **records()[2],
        "local_id": "new",
        "title": "A distinct application",
        "claim": "An application follows under additional conditions",
        "passage_ids": ["p1"],
    }
    reuse = {
        "id": "n1",
        "reason": "Exactly the same corrected result",
        "passage_ids": ["p1"],
    }

    class FixtureProvider:
        def __init__(self, *args):
            pass

        def complete(self, system, payload, task, *args):
            receipt = {
                "request_id": task,
                "requested_model": "fixture",
                "time": "2026-10-17T00:00:00Z",
            }
            if task.startswith("extract:"):
                return {
                    "relevant": True,
                    "contributions": [candidate],
                    "reuse": [reuse],
                    "relations": [
                        {
                            "from": ["n1"],
                            "to": "new",
                            "predicate": "premise_for",
                            "scope": "Finite input",
                            "warrant": "The finite result entails the application within this scope.",
                            "passage_ids": ["p1"],
                        }
                    ],
                }, receipt
            return {
                "source_relevant": True,
                "contributions": [
                    {
                        "local_id": "new",
                        "decision": "supported",
                        "rationale": "Checked new move",
                    }
                ],
                "reuse": [
                    {
                        "index": 0,
                        "decision": "supported",
                        "rationale": "Checked identity",
                    }
                ],
                "relations": [
                    {
                        "index": 0,
                        "decision": "supported",
                        "rationale": "Checked entailment",
                    }
                ],
            }, receipt

    monkeypatch.setattr(curate, "Provider", FixtureProvider)
    topic = {
        "id": "M01",
        "pillar": "mathematics",
        "title": "Finite applications",
        "documented_contributions": [existing],
    }
    result = curate.process_source(atlas_root, topic, "https://example.org/application")
    edge = next(r for r in result["records"] if r["type"] == "relation")
    assert edge["premises"] == [{"id": "n1", "revision": 2}]
    assert result["screened"]["accepted_nodes"] == 1
    assert not any(r["id"] == "n1" for r in result["records"])
