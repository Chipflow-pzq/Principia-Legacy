import copy
import json
from pathlib import Path
import pytest
from principia_legacy.common import seal, write_json
from principia_legacy.authoring_store import Commit, recover, writer, reserve, settle
from principia_legacy.admission_versions import prepare_versions
from principia_legacy.curate import make_review
from principia_legacy.records import validate
from test_core import records


def test_source_extension_preserves_historical_pins_and_new_reviews():
    existing = records()
    source = copy.deepcopy(next(r for r in existing if r["type"] == "source"))
    source["anchors"].append(
        {**source["anchors"][0], "id": "a2", "text_hash": "new-anchor"}
    )
    seal(source)
    node = copy.deepcopy(next(r for r in existing if r["type"] == "contribution"))
    node["id"] = "new-insight"
    node["claim"] = "A distinct insight supported by the additional passage"
    node["anchors"][0]["anchor_id"] = "a2"
    seal(node)
    review = make_review(
        node,
        "Pinned passage supports the claim",
        {"request_id": "test", "time": "2026-10-26"},
    )
    before = copy.deepcopy(existing)
    additions, _, withheld = prepare_versions(existing, [source, node, review])
    assert existing == before and not withheld
    new_source = next(r for r in additions if r["type"] == "source")
    assert new_source["revision"] == 2 and len(new_source["anchors"]) == 2
    new_node = next(r for r in additions if r["type"] == "contribution")
    new_review = next(r for r in additions if r["type"] == "review")
    assert new_node["anchors"][0]["source_revision"] == 2
    assert new_review["evidence_checked"] == new_node["anchors"]
    assert new_review["target"]["content_hash"] == new_node["content_hash"]
    assert not validate([*existing, *additions])
    again, _, _ = prepare_versions([*existing, *additions], [source, node, review])
    assert again == []


def test_existing_identity_is_not_silently_rewritten():
    existing = records()
    node = copy.deepcopy(next(r for r in existing if r["type"] == "contribution"))
    node["explanation"] = "A changed interpretation requiring a correction"
    seal(node)
    additions, _, withheld = prepare_versions(existing, [node])
    assert additions == [] and withheld[0]["id"] == node["id"]


def test_interrupted_multi_file_commit_rolls_forward(tmp_path, monkeypatch):
    import principia_legacy.authoring_store as store

    with writer(tmp_path):
        commit = Commit(tmp_path, "fixture")
        commit.json(tmp_path / "corpus/a.json", {"version": 1})
        commit.json(tmp_path / "manifests/b.json", {"version": 1})
        original = store.atomic_write

        def interrupted(path, text):
            if Path(path) == tmp_path / "manifests/b.json":
                raise OSError("simulated interruption")
            original(path, text)

        monkeypatch.setattr(store, "atomic_write", interrupted)
        with pytest.raises(OSError):
            commit.publish()
    assert (tmp_path / "corpus/a.json").exists()
    monkeypatch.setattr(store, "atomic_write", original)
    with writer(tmp_path):
        recover(tmp_path)
    assert json.loads((tmp_path / "manifests/b.json").read_text()) == {"version": 1}
    with writer(tmp_path):
        recover(tmp_path)
    journal = next((tmp_path / ".work/commits").glob("*/journal.json"))
    assert json.loads(journal.read_text())["state"] == "committed"


def test_recovery_refuses_external_changes(tmp_path, monkeypatch):
    import principia_legacy.authoring_store as store

    original = store.recover
    monkeypatch.setattr(store, "recover", lambda root: None)
    with writer(tmp_path):
        commit = Commit(tmp_path, "fixture")
        commit.text(tmp_path / "canonical.jsonl", "planned")
        commit.publish()
    (tmp_path / "canonical.jsonl").write_text("unrelated edit")
    monkeypatch.setattr(store, "recover", original)
    with writer(tmp_path), pytest.raises(ValueError, match="conflicts"):
        recover(tmp_path)
    assert (tmp_path / "canonical.jsonl").read_text() == "unrelated edit"


def test_unknown_usage_keeps_reservation_and_stops_new_requests(tmp_path):
    write_json(
        tmp_path / "config/provider_budget.json",
        {
            "models": {
                "model": {"input_cny_per_million": 2, "output_cny_per_million": 8}
            },
            "working_ceiling_cny": 10,
            "unknown_attempt_pause": 1,
        },
    )
    price = reserve(
        tmp_path,
        "model",
        {"messages": [{"content": "evidence"}], "max_tokens": 100},
        "first",
    )
    settle(tmp_path, "first", price, {})
    with pytest.raises(RuntimeError, match="uncertain-usage"):
        reserve(tmp_path, "model", {"messages": [], "max_tokens": 100}, "second")


def test_queued_request_timeout_is_explicitly_unsent_and_cleans_waiter(tmp_path):
    from contextlib import ExitStack
    import sqlite3
    from principia_legacy.authoring_store import provider_slot, QueueBusy

    with ExitStack() as stack:
        for _ in range(4):
            stack.enter_context(provider_slot(tmp_path, "fixture"))
        with pytest.raises(QueueBusy):
            with provider_slot(tmp_path, "fixture", wait_seconds=0):
                pytest.fail("A fifth transmission slot was granted")
        with sqlite3.connect(tmp_path / ".work/provider-slots.sqlite") as db:
            assert db.execute("SELECT count(*) FROM slots").fetchone()[0] == 4
            assert db.execute("SELECT count(*) FROM waiting").fetchone()[0] == 0
    with sqlite3.connect(tmp_path / ".work/provider-slots.sqlite") as db:
        assert db.execute("SELECT count(*) FROM slots").fetchone()[0] == 0


def test_queue_timeout_cannot_be_recorded_as_a_charged_generation(
    tmp_path, monkeypatch
):
    from contextlib import contextmanager
    from principia_legacy import providers
    from principia_legacy.authoring_store import QueueBusy

    monkeypatch.setenv("SILICONFLOW_API_KEY", "fixture-key")

    @contextmanager
    def busy(*args):
        raise QueueBusy("No transmission slot")
        yield

    monkeypatch.setattr(providers, "provider_slot", busy)
    monkeypatch.setattr(
        providers.urllib.request,
        "urlopen",
        lambda *a, **k: pytest.fail("Unsent request reached network"),
    )
    with pytest.raises(QueueBusy):
        providers.Provider(tmp_path).complete("Fixture", {}, "queue-fixture")
    receipt = json.loads(next((tmp_path / ".work/receipts").glob("*.json")).read_text())
    assert receipt["state"] == "not_submitted" and receipt["submitted"] is False
    assert receipt["usage"] == {"prompt_tokens": 0, "completion_tokens": 0}


def test_waiting_order_and_model_cooldown_do_not_starve_other_models(tmp_path):
    import os
    import sqlite3
    from principia_legacy.authoring_store import (
        provider_slot,
        provider_cooldown,
        QueueBusy,
    )

    with provider_slot(tmp_path, "setup"):
        pass
    path = tmp_path / ".work/provider-slots.sqlite"
    with sqlite3.connect(path) as db:
        db.execute(
            "INSERT INTO waiting(token,pid,model) VALUES(?,?,?)",
            ("earlier", os.getpid(), "A"),
        )
    with pytest.raises(QueueBusy):
        with provider_slot(tmp_path, "B", wait_seconds=0):
            pytest.fail("New arrival skipped an eligible earlier request")
    provider_cooldown(tmp_path, "A", 30)
    with provider_slot(tmp_path, "B", wait_seconds=0):
        with sqlite3.connect(path) as db:
            assert db.execute("SELECT token FROM waiting").fetchall() == [("earlier",)]
