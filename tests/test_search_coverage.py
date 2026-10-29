# ruff: noqa: F811 -- shared pytest fixture
"""Catalogue presence must not masquerade as an explained answer."""

import sys
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import pytest
from test_core import atlas_root  # noqa: F401
from test_works import add_works

from principia_legacy import semantic
from principia_legacy.authoring_store import Commit, writer
from principia_legacy.common import read_json, write_json
from principia_legacy.curate import relation_targets
from principia_legacy.storage import Atlas, build

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_work_catalog import compile_catalog
from connect_sources import labelled_context, resolve_labels


def test_named_method_is_not_replaced_by_scattered_generic_words(atlas_root):
    from test_core import records

    from principia_legacy.common import seal, write_lines

    items = records()
    items[1]["title"] = "Differences in tissue relaxation"
    items[2]["title"] = "Difference-in-differences estimation"
    items[3]["title"] = "Differences between algorithms"
    write_lines(atlas_root / "corpus/records.jsonl", [seal(r) for r in items])
    build(atlas_root)
    with closing(Atlas(atlas_root)) as atlas:
        result = atlas.search("difference in differences")
        assert [r["id"] for r in result["results"]] == ["n2"]
        assert not atlas.search("difference in differences", pillar="physics")[
            "results"
        ]


def test_example_clause_does_not_require_literal_prose_in_every_match(atlas_root):
    with closing(Atlas(atlas_root)) as atlas:
        result = atlas.search("finite theorems such as compactness")
        # Singular/plural spelling can vary; all visible results must be from
        # the actual finite-theorem fixture, not an invented compactness record.
        assert result["results"]
        assert all("Finite theorem" in r["title"] for r in result["results"])


def test_compiled_index_is_readable_after_atomic_replacement(atlas_root):
    index = atlas_root / "build/atlas.sqlite"
    index.chmod(0o600)
    before = index.stat().st_ino
    build(atlas_root)
    assert index.stat().st_ino != before
    assert index.stat().st_mode & 0o777 == 0o644
    with closing(Atlas(atlas_root)) as reader:
        assert reader.info()["release_id"] == "working"


def test_connection_labels_preserve_exact_evidence_without_guessing():
    anchor = {"source_id": "s-exact", "source_revision": 2, "anchor_id": "p9"}
    payload = {
        "nodes": [
            {"id": "long-a", "anchors": [anchor]},
            {"id": "long-b", "anchors": [anchor]},
        ],
        "evidence": {"s-exact@2:p9": {"reference": anchor, "passage": "Fixture"}},
        "existing_connections": [{"from": ["long-a"], "to": "long-b"}],
    }
    context, nodes, evidence = labelled_context(payload)
    assert context["nodes"][0]["evidence_keys"] == ["E1"]
    assert context["evidence"]["E1"]["reference"] == anchor
    proposal = {
        "from": ["N1"],
        "to": "N2",
        "evidence_keys": ["E1"],
        "predicate": "supports",
        "scope": "scope",
        "warrant": "warrant",
    }
    resolved = resolve_labels(proposal, nodes, evidence)
    assert resolved["from"] == ["long-a"]
    assert resolved["to"] == "long-b"
    assert resolved["evidence_keys"] == ["s-exact@2:p9"]
    for unknown in ("N22", ["N2"], None):
        with pytest.raises(ValueError, match="Unknown request-local"):
            resolve_labels({**proposal, "to": unknown}, nodes, evidence)


def test_singleton_relation_target_is_only_a_format_repair():
    original = {"from": ["a", "b"], "to": ["c"], "predicate": "premise_for"}
    normalized, changes = relation_targets([original])
    assert normalized == [{**original, "to": "c"}]
    assert original["to"] == ["c"]
    assert changes[0]["index"] == 0
    with pytest.raises(ValueError, match="one conclusion"):
        relation_targets([{**original, "to": ["c", "d"]}])


def test_explicit_reader_history_preserves_old_links_and_identifies_current(atlas_root):
    from principia_legacy.release import freeze

    freeze(atlas_root, "1.5.0-review4")
    freeze(atlas_root, "1.5.0-review5")
    write_json(atlas_root / "config/reader_history.json", ["1.5.0-review4"])
    build(atlas_root, "1.5.0-review5")
    with closing(Atlas(atlas_root, "1.5.0-review4")) as old:
        assert old.info()["release_id"] == "1.5.0-review4"
        assert old.info()["current_release_id"] == "1.5.0-review5"


def test_catalogue_paper_gains_checked_insights_without_a_duplicate_work(atlas_root):
    seed = {
        "id": "selected-paper",
        "title": "Selected source work",
        "kind": "paper",
        "subjects": ["mathematics"],
        "summary": "Selected paper",
        "people": [],
        "topic_ids": ["M01"],
        "source_refs": [],
        "provenance": [
            {
                "url": "https://example.org/paper",
                "title": "Test paper",
                "note": "Fixture metadata",
            }
        ],
        "evidence_source_ids": ["s1"],
    }
    write_json(atlas_root / "config/extra_works.json", [seed])
    with writer(atlas_root):
        commit = Commit(atlas_root, "test-bind-source")
        compile_catalog(atlas_root, commit)
        commit.publish()
    works = read_json(atlas_root / "manifests/works.json")
    assert [w["id"] for w in works] == ["selected-paper"]
    assert works[0]["source_refs"][0]["id"] == "s1"
    build(atlas_root)
    with closing(Atlas(atlas_root)) as atlas:
        assert atlas.work("selected-paper")["work"]["insight_count"] == 3
    write_json(
        atlas_root / "config/extra_works.json",
        [seed, {**seed, "id": "ambiguous-paper"}],
    )
    with writer(atlas_root), pytest.raises(ValueError, match="Ambiguous explicit"):
        compile_catalog(atlas_root, Commit(atlas_root, "ambiguous-binding"))


def test_search_topic_cards_and_inventory_report_real_content(atlas_root):
    add_works(atlas_root)
    with closing(Atlas(atlas_root)) as atlas:
        topic = next(t for t in atlas.search("finite")["topics"] if t["id"] == "M01")
        assert topic["contribution_count"] == 3
        assert topic["relation_count"] == 1
        coverage = atlas.coverage_summary()
        assert coverage["release_id"] == atlas.release
        assert coverage["subjects"]["mathematics"]["insights"] == 3
        assert coverage["subjects"]["mathematics"]["works_with_insights"] == 2
        assert coverage["human_reviewed_insights"] == 0


def test_semantic_work_expansion_is_bounded_pinned_and_filtered(atlas_root):
    add_works(atlas_root)

    class Index:
        def rank(self, query, pillar, human):
            return (
                []
                if human or pillar == "physics"
                else [(0.7, {"id": "w1", "kind": "works"})]
            )

    with (
        closing(Atlas(atlas_root)) as atlas,
        patch.object(semantic, "load", return_value=Index()),
    ):
        result = atlas.search("unindexed research question", limit=1)
        assert result["works"][0]["id"] == "w1"
        assert result["results"][0]["id"] == "n1"
        assert result["people"][0]["id"] == "person-test"
        assert result["search_interpretation"]["membership_expansion"] == [
            {"id": "n1", "via_kind": "works", "via_id": "w1"}
        ]
        assert result["results"][0]["revision"] == atlas.get("n1")["revision"]
        assert not atlas.search("unindexed research question", human=True)["results"]
        assert not atlas.search("unindexed research question", pillar="physics")[
            "results"
        ]
