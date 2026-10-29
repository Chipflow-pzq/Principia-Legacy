import copy
from principia_legacy.coverage import assessed_route


def route():
    nodes = [
        {
            "id": f"n{i}",
            "revision": 1,
            "content_hash": f"h{i}",
            "limits": ["Finite scope"],
        }
        for i in range(8)
    ]
    edges = [
        {
            "id": f"r{i}",
            "content_hash": f"e{i}",
            "premises": [{"id": f"n{i}", "revision": 1}],
            "conclusion": {"id": f"n{i + 1}", "revision": 1},
        }
        for i in range(7)
    ]
    topic = {"endpoint": "n7", "gaps": ["Historical priority unresolved"]}
    assessment = {
        "outcome": "representative_route_supported",
        "rationale": "A scoped reading route",
        "limitations": ["Not a historical proof"],
        "endpoint": "n7",
        "core_insight_ids": [n["id"] for n in nodes],
        "relation_ids": [r["id"] for r in edges],
        "foundational_insight_ids": ["n0"],
        "record_hashes": {r["id"]: r["content_hash"] for r in nodes + edges},
    }
    return topic, assessment, nodes, edges


def test_route_readiness_requires_current_pins_complete_premises_and_connected_core():
    assert assessed_route(*route())["ready"]
    for alteration in (
        "stale",
        "missing_premise",
        "disconnected",
        "wrong_endpoint",
        "missing_pin",
    ):
        topic, assessment, nodes, edges = copy.deepcopy(route())
        if alteration == "stale":
            nodes[0]["content_hash"] = "changed"
        elif alteration == "missing_premise":
            edges[0]["premises"].append({"id": "outside", "revision": 1})
        elif alteration == "disconnected":
            edges[3]["conclusion"]["id"] = "n3"
        elif alteration == "wrong_endpoint":
            topic["endpoint"] = "n6"
        elif alteration == "missing_pin":
            assessment["record_hashes"].pop("n0")
        assert not assessed_route(topic, assessment, nodes, edges)["ready"], alteration


def test_readiness_is_separate_from_human_review_and_unassessed_coverage():
    topic, _, nodes, edges = route()
    assert (
        assessed_route(topic, {}, nodes, edges)["review"]
        == "not_assessed_or_incomplete"
    )
    result = assessed_route(*route())
    assert result["review"] == "machine_editorial"
    assert "not human review" in result["notice"]
