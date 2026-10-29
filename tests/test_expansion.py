"""The upgrade must preserve the archive even when new curation is unreliable."""

# ruff: noqa: F811 -- pytest fixture imported from shared test corpus
import copy
import pytest
from principia_legacy.common import read_lines, seal, write_json, write_lines
from principia_legacy.expansion import admit, validate_plan
from principia_legacy.curate import selected_passages
from principia_legacy.storage import corpus, build, Atlas
from principia_legacy.release import freeze
from test_core import atlas_root, records  # noqa: F401


def test_expansion_keeps_frozen_records_and_refuses_revision_collision(atlas_root):
    freeze(atlas_root, "original")
    before = copy.deepcopy(corpus(atlas_root))
    node = copy.deepcopy(records()[1])
    node["claim"] = "A conflicting replacement of an existing revision"
    seal(node)
    outcomes = [{"dossier": "M01", "state": "succeeded", "result": {"records": [node]}}]
    admit(atlas_root, {"id": "conflict-check"}, outcomes)
    assert outcomes[0]["admission"] == "needs_revision_patch"
    assert corpus(atlas_root) == before
    build(atlas_root, "original")
    atlas = Atlas(atlas_root, "original")
    assert atlas.get("n1")["claim"] == "A finite result"
    atlas.close()


def test_expansion_allowance_survives_resume(atlas_root):
    plan = {"id": "limited", "new_node_allowance": 1}
    nodes = []
    for id in ("new-a", "new-b"):
        n = copy.deepcopy(records()[1])
        n["id"] = id
        n["claim"] = "A distinct result for " + id
        seal(n)
        nodes.append(n)

    def outcome(n):
        return {"dossier": "M01", "state": "succeeded", "result": {"records": [n]}}

    first = [outcome(n) for n in nodes]
    admit(atlas_root, plan, first)
    assert first[1]["admission"] == "stopped_at_expansion_allowance"
    resumed = [outcome(n) for n in nodes]
    admit(atlas_root, plan, resumed)
    assert resumed[1]["admission"] == "stopped_at_expansion_allowance"
    assert [
        r["id"] for r in read_lines(atlas_root / "corpus/expansions/limited.jsonl")
    ] == ["new-a"]


def test_depth_extension_needs_explanation():
    plan = {
        "id": "depth-plan",
        "frozen_checklists": {"M01": []},
        "assignments": [
            {
                "dossier": "M01",
                "url": "https://example.org/paper",
                "need": "Proof boundary",
                "role": "boundary",
                "depth": 7,
            }
        ],
    }
    with pytest.raises(ValueError, match="explanatory need"):
        validate_plan(plan, {"M01": {}})
    plan["assignments"][0]["extension_reason"] = (
        "This documented precursor resolves the explicitly frozen proof assumption."
    )
    assert len(validate_plan(plan, {"M01": {}})) == 1


def test_passage_retrieval_can_reach_limits_after_long_intro():
    source = {
        "passages": [
            {
                "id": f"p{i}",
                "text": ("unrelated background " * 50)
                if i < 20
                else "transport regularization limitation " * 30,
            }
            for i in range(25)
        ]
    }
    selected = selected_passages(
        source, cap=3000, query="transport regularization limitation"
    )
    assert any(int(p["id"][1:]) >= 20 for p in selected)
    assert sum(len(p["text"]) for p in selected) <= 3000
    assert selected == sorted(selected, key=lambda p: int(p["id"][1:]))


def test_legacy_curation_merge_is_append_only_and_checks_all_batches(atlas_root):
    from principia_legacy.curate import merge_results

    freeze(atlas_root, "original")
    before = copy.deepcopy(corpus(atlas_root))
    original_path = atlas_root / "corpus/records.jsonl"
    original_bytes = original_path.read_bytes()
    extra = copy.deepcopy(records()[1])
    extra["id"] = "separate-batch"
    seal(extra)
    write_lines(atlas_root / "corpus/expansions/already.jsonl", [extra])
    write_json(
        atlas_root / ".work/curated/cached.json",
        {"dossier": "M01", "state": "succeeded", "records": [extra]},
    )
    merge_results(atlas_root)
    assert original_path.read_bytes() == original_bytes
    assert len([r for r in corpus(atlas_root) if r["id"] == "separate-batch"]) == 1
    assert all(r in corpus(atlas_root) for r in before)


def test_source_title_does_not_absorb_body_text():
    from principia_legacy.acquire import ArticleParser

    parser = ArticleParser()
    parser.feed(
        "<html><head><title>A precise paper title</title></head><body><p>A separate paragraph explaining a conceptual result.</p></body></html>"
    )
    assert "".join(parser.title_parts) == "A precise paper title"
    assert parser.lines[-1] == "A separate paragraph explaining a conceptual result."


def test_source_body_caps_size_and_slow_delivery(monkeypatch):
    import io
    from principia_legacy.acquire import bounded_body

    assert bounded_body(io.BytesIO(b"abc"), byte_cap=3) == b"abc"
    with pytest.raises(ValueError, match="download cap"):
        bounded_body(io.BytesIO(b"abcd"), byte_cap=3)
    ticks = iter([0, 0, 91])
    monkeypatch.setattr("principia_legacy.acquire.time.monotonic", lambda: next(ticks))
    with pytest.raises(TimeoutError, match="total time cap"):
        bounded_body(io.BytesIO(b"abc"))


def test_quarantined_main_result_is_not_offered_as_a_reader_action(atlas_root):
    from principia_legacy.lifecycle import prepare_patch, apply_patch

    original = next(r for r in corpus(atlas_root) if r["id"] == "n3")
    edited = copy.deepcopy(original)
    edited["revision"] += 1
    edited["limits"].append("The result is awaiting a revised scope check.")
    patch = prepare_patch(
        atlas_root,
        {
            "reason": "scope correction",
            "base_hashes": {"n3": original["content_hash"]},
            "records": [edited],
        },
    )
    write_json(atlas_root / "patch.json", patch)
    apply_patch(atlas_root, atlas_root / "patch.json")
    build(atlas_root)
    atlas = Atlas(atlas_root)
    topic = atlas.dossiers()["dossiers"][0]
    assert topic["endpoint"] is None
    assert topic["declared_endpoint"] == "n3"
    assert topic["endpoint_revision"] is None
    atlas.close()


def test_topic_neighborhood_preserves_endpoint_and_expands_as_a_prefix(atlas_root):
    build(atlas_root)
    atlas = Atlas(atlas_root)
    small = atlas.neighborhood(dossier="M01", limit=1)
    large = atlas.neighborhood(dossier="M01", limit=2)
    assert [n["id"] for n in small["contributions"]] == ["n3"]
    assert small["available_count"] == large["available_count"] == 3
    assert {n["id"] for n in small["contributions"]} <= {
        n["id"] for n in large["contributions"]
    }
    atlas.close()


def test_completed_source_batch_resumes_without_credentials_or_writes(atlas_root):
    from principia_legacy.expansion import expand
    from principia_legacy.common import digest

    plan = {"id": "finished", "assignments": []}
    report = {
        "plan_hash": digest(plan),
        "completed_at": "2026-10-12",
        "admission": {"new_records": 0},
    }
    write_json(atlas_root / "plan.json", plan)
    write_json(atlas_root / "reports/expansion/finished.json", report)
    write_lines(atlas_root / "corpus/expansions/finished.jsonl", [])
    registry = (atlas_root / "manifests/FRONTIER_REGISTRY.jsonl").read_bytes()
    assert (
        expand(atlas_root, atlas_root / "plan.json", env_file="/does-not-exist")
        == report
    )
    assert (atlas_root / "manifests/FRONTIER_REGISTRY.jsonl").read_bytes() == registry


def test_reworded_title_cannot_readmit_same_claim_or_inherit_arrows():
    from principia_legacy.admission_versions import prepare_versions

    existing = records()
    duplicate = copy.deepcopy(existing[1])
    duplicate.update(id="retitled-copy", title="A new title for the same move")
    seal(duplicate)
    result, _, withheld = prepare_versions(existing, [duplicate])
    assert not result
    assert withheld[0]["possible_duplicate_of"] in {
        r["id"] for r in existing if r["type"] == "contribution"
    }

    relation = copy.deepcopy(next(r for r in existing if r["type"] == "relation"))
    relation["id"] = "relation-from-duplicate"
    relation["premises"] = [
        {k: duplicate[k] for k in ("id", "revision", "content_hash")}
    ]
    seal(relation)
    result, _, withheld = prepare_versions(existing, [duplicate, relation])
    assert not result
    assert {r["id"] for r in withheld} == {duplicate["id"], relation["id"]}

    # An independent named formulation is not merged with the first discovery.
    independent = copy.deepcopy(duplicate)
    independent["attribution"] = [
        {
            "name": "Independent contributor",
            "role": "original contributor",
            "evidence_note": "Distinct documented formulation",
        }
    ]
    seal(independent)
    result, _, withheld = prepare_versions(existing, [independent])
    assert not withheld and result[0]["id"] == independent["id"]


def test_same_batch_duplicate_is_quarantined_without_changing_math_case():
    from principia_legacy.admission_versions import prepare_versions

    first = copy.deepcopy(records()[1])
    second = copy.deepcopy(first)
    second.update(id="retitled-copy", title="Another title")
    seal(second)
    result, _, withheld = prepare_versions([], [first, second])
    assert [r["id"] for r in result] == [first["id"]]
    assert withheld[0]["id"] == second["id"]
    second["claim"] = first["claim"].upper()
    seal(second)
    result, _, withheld = prepare_versions([], [first, second])
    assert len(result) == 2 and not withheld
