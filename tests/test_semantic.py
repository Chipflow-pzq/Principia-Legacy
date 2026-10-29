# ruff: noqa: F811 -- shared pytest fixture
"""Semantic fallback is optional, pinned, bounded and cannot bypass filters."""

from contextlib import closing
from unittest.mock import patch
from test_core import atlas_root  # noqa: F401
from principia_legacy.storage import Atlas
from principia_legacy import semantic


class Index:
    def rank(self, query, pillar, human):
        assert query == "missing paraphrase"
        return [] if pillar or human else [(0.7, {"kind": "results", "id": "n1"})]


def test_semantic_does_not_replace_exact_matches_or_filters(atlas_root):
    with (
        closing(Atlas(atlas_root)) as a,
        patch.object(semantic, "load", return_value=Index()),
    ):
        assert a.search("finite")["search_interpretation"]["match_mode"] == "direct"
        result = a.search("missing paraphrase")
        assert result["results"][0]["id"] == "n1"
        assert result["search_interpretation"]["match_mode"] == "semantic"
        assert not a.search("missing paraphrase", human=True)["results"]
        assert not a.search("missing paraphrase", pillar="physics")["results"]


def test_optional_service_unavailable_leaves_standard_reader_usable(atlas_root):
    with (
        closing(Atlas(atlas_root)) as a,
        patch.object(semantic, "load", side_effect=ImportError()),
    ):
        assert a.search("missing paraphrase")["totals"]["ideas"] == 0
        assert a.search("finite")["results"]


def test_related_concepts_are_explicit_and_keep_human_filter(atlas_root):
    from principia_legacy.common import write_json
    from principia_legacy.storage import build
    from test_works import add_works

    add_works(atlas_root)
    write_json(
        atlas_root / "config/search_concepts.json",
        [{"terms": ["unindexed mechanism"], "related": ["finite"]}],
    )
    build(atlas_root)
    with closing(Atlas(atlas_root)) as a:
        result = a.search("unindexed mechanism")
        assert result["results"]
        assert result["search_interpretation"]["match_mode"] == "related"
        assert "No direct matches" in result["search_interpretation"]["notice"]
        assert not a.search("unindexed mechanism", human=True)["results"]


def test_expanded_phrase_requires_proximity():
    import sqlite3
    from principia_legacy.retrieval import planned_expression

    with sqlite3.connect(":memory:") as db:
        db.execute("CREATE VIRTUAL TABLE docs USING fts5(text)")
        db.executemany(
            "INSERT INTO docs VALUES(?)",
            [
                ("neural state estimation in a population",),
                ("neural population dynamics",),
            ],
        )
        expression = planned_expression(
            {
                "queries": ["neuronal state space", "neural population dynamics"],
                "primary_queries": ["neuronal state space"],
            }
        )
        assert db.execute(
            "SELECT text FROM docs WHERE docs MATCH ?", (expression,)
        ).fetchall() == [("neural population dynamics",)]
