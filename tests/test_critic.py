from principia_legacy.critic import check_candidates


class Critic:
    model = "test-exact-model"

    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail

    def complete(self, prompt, payload, task, max_tokens):
        self.calls.append(payload)
        if self.fail and len(self.calls) == 2:
            raise TimeoutError("fixture unfinished request")
        out = {"source_relevant": True}
        for kind in ["contributions", "relations", "reuse"]:
            field = "local_id" if kind == "contributions" else "index"
            out[kind] = [
                {
                    field: case["local_id"] if field == "local_id" else i,
                    "decision": "supported",
                    "rationale": "Fixture exact passage checked",
                }
                for i, case in enumerate(payload[kind])
            ]
        return out, {
            "request_id": task,
            "trace_id": task,
            "returned_model": self.model,
            "time": "2026-10-26",
        }


def test_critic_does_not_resend_a_whole_chapter_and_pins_individual_receipts():
    provider = Critic()
    passages = [{"id": f"p{i}", "text": "X" * 5000} for i in range(30)]
    nodes = [
        {"local_id": f"n{i}", "claim": "Synthetic scope", "passage_ids": [f"p{i + 5}"]}
        for i in range(8)
    ]
    edges = [
        {"from": ["n0"], "to": "n1", "predicate": "premise_for", "passage_ids": ["p5"]}
        for _ in range(7)
    ]
    result, _ = check_candidates(
        provider, "fixture", "Topic", passages, nodes, edges, [], []
    )
    assert len(provider.calls) == 4
    assert all(
        sum(len(p["text"]) for p in call["passages"]) <= 36000
        for call in provider.calls
    )
    assert {c["index"] for c in result["relations"]} == set(range(7))
    assert len({c["receipt"]["request_id"] for c in result["contributions"]}) == 2
    assert {n["local_id"] for n in provider.calls[-1]["endpoint_contributions"]} == {
        "n0",
        "n1",
    }
    meanings = provider.calls[-1]["predicate_meanings"]
    assert set(meanings) == {"premise_for"}
    assert "inferential conclusion" in meanings["premise_for"]["meaning"]
    assert "predicate_meanings" not in provider.calls[0]


def test_failed_critic_batch_is_withheld_without_replaying_completed_siblings():
    provider = Critic(fail=True)
    nodes = [{"local_id": f"n{i}", "passage_ids": ["p1"]} for i in range(8)]
    result, _ = check_candidates(
        provider,
        "fixture",
        "Topic",
        [{"id": "p1", "text": "Synthetic evidence"}],
        nodes,
        [],
        [],
        [],
    )
    assert len(provider.calls) == 2
    assert (
        len([c for c in result["contributions"] if c["decision"] == "supported"]) == 5
    )
    assert (
        len(
            [
                c
                for c in result["contributions"]
                if c["decision"] == "insufficient_context"
            ]
        )
        == 3
    )
    assert result["failures"] and result["source_relevant"]


def test_oversized_required_passage_is_not_truncated_or_sent():
    provider = Critic()
    result, _ = check_candidates(
        provider,
        "fixture",
        "Topic",
        [{"id": "p1", "text": "X" * 50000}],
        [{"local_id": "n1", "passage_ids": ["p1"]}],
        [],
        [],
        [],
    )
    assert not provider.calls
    assert result["contributions"][0]["decision"] == "insufficient_context"
