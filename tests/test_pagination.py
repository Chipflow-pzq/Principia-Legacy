# ruff: noqa: F811 -- pytest fixture imported from shared corpus
from contextlib import closing
import copy
import json
import pytest
from principia_legacy.common import seal, write_lines, digest
from principia_legacy.storage import Atlas, build
from principia_legacy import exploration_index
from test_core import atlas_root, records  # noqa: F401


def test_snapshot_compression_preserves_identity_and_legacy_compatibility():
    from principia_legacy.common import encode_snapshot, decode_snapshot

    value = {"release_id": "fixture", "history": ["Repeated immutable metadata"] * 1000}
    compressed = encode_snapshot(value)
    assert len(compressed) < len(json.dumps(value)) / 10
    assert digest(decode_snapshot(compressed)) == digest(value)
    assert decode_snapshot(json.dumps(value)) == value
    with pytest.raises(ValueError, match="Invalid"):
        decode_snapshot(compressed[:-5])


def test_compilation_does_not_hold_authoring_lock_during_indexing(
    atlas_root, monkeypatch
):
    import sqlite3
    from principia_legacy import query_index

    original = query_index.populate
    acquired = []

    def populate(*args):
        with (
            closing(
                sqlite3.connect(atlas_root / ".work/coordination.sqlite", timeout=0.1)
            ) as db,
            db,
        ):
            db.execute("BEGIN IMMEDIATE")
            acquired.append(True)
        return original(*args)

    monkeypatch.setattr(query_index, "populate", populate)
    build(atlas_root)
    assert acquired


@pytest.mark.parametrize(
    "checkpoint", ["before-checkpoint", "1.5.0-qa1", "1.5.0-review1"]
)
def test_internal_checkpoints_are_only_decoded_for_explicit_restoration(
    atlas_root, monkeypatch, checkpoint
):
    from principia_legacy import compiler
    from principia_legacy.release import freeze

    freeze(atlas_root, checkpoint)
    original = compiler.read_json
    decoded = []

    def read(path, *args):
        decoded.append(str(path))
        return original(path, *args)

    monkeypatch.setattr(compiler, "read_json", read)
    build(atlas_root)
    assert not any(path.endswith(checkpoint + ".json") for path in decoded)
    build(atlas_root, checkpoint)
    assert any(path.endswith(checkpoint + ".json") for path in decoded)
    with closing(Atlas(atlas_root, checkpoint)) as reader:
        assert reader.search("finite")["totals"]["ideas"] == 3


def test_cursor_pins_filter_limit_and_snapshot(atlas_root):
    with closing(Atlas(atlas_root)) as a:
        page = a.search("finite", limit=1)
        assert page["next_cursor"] and page["totals"]["ideas"] == 3
        following = a.search("finite", limit=1, cursor=page["next_cursor"])
        assert page["results"][0]["id"] != following["results"][0]["id"]
        assert following["results"] == a.search("finite", limit=1, offset=1)["results"]
        for kwargs in [
            {"query": "different", "limit": 1},
            {"query": "finite", "limit": 2},
            {"query": "finite", "limit": 1, "pillar": "physics"},
        ]:
            with pytest.raises(ValueError, match="cursor"):
                a.search(cursor=page["next_cursor"], **kwargs)
        cursor = page["next_cursor"]
    changed = records()
    changed[1]["explanation"] += " Changed interpretation."
    seal(changed[1])
    write_lines(atlas_root / "corpus/records.jsonl", changed)
    build(atlas_root)
    with closing(Atlas(atlas_root)) as a, pytest.raises(ValueError, match="cursor"):
        a.search("finite", limit=1, cursor=cursor)


def test_large_topic_list_reaches_every_record_beyond_graph_limit(atlas_root):
    values = records()
    base = values[1]
    for i in range(205):
        item = copy.deepcopy(base)
        item["id"] = f"extra-{i:03}"
        item["title"] = f"Extra {i}"
        values.append(seal(item))
    write_lines(atlas_root / "corpus/records.jsonl", values)
    build(atlas_root)
    with closing(Atlas(atlas_root)) as a:
        ids, cursor = set(), None
        while True:
            page = a.topic_contributions("M01", limit=40, cursor=cursor)
            batch = {n["id"] for n in page["contributions"]}
            assert not ids & batch
            ids |= batch
            cursor = page["next_cursor"]
            if not cursor:
                break
        assert len(ids) == page["total"] == 208
        assert len(a.neighborhood(dossier="M01", limit=200)["contributions"]) <= 200


def test_profile_pages_are_bounded_and_cursors_cannot_cross_entities(atlas_root):
    values = records()
    for i in range(105):
        item = copy.deepcopy(values[1])
        item["id"] = f"profile-extra-{i:03}"
        values.append(seal(item))
    write_lines(atlas_root / "corpus/records.jsonl", values)
    build(atlas_root)
    with closing(Atlas(atlas_root)) as a:
        people = a.people()["people"]
        person = next(p for p in people if p["name"] == "Test author")
        page = a.person(person["id"])
        assert len(page["contributions"]) == 40
        assert page["contribution_total"] == 108
        ids = {n["id"] for n in page["contributions"]}
        cursor = page["next_cursor"]
        with pytest.raises(ValueError, match="cursor"):
            a.person(person["id"], human=True, cursor=cursor)
        while cursor:
            page = a.person(person["id"], cursor=cursor)
            batch = {n["id"] for n in page["contributions"]}
            assert not ids & batch
            ids |= batch
            cursor = page["next_cursor"]
        assert len(ids) == 108
        assert not a.topic_contributions("M01", human=True)["contributions"]


def test_compact_shards_and_hydration_have_exact_snapshot_pins(atlas_root):
    with closing(Atlas(atlas_root)) as a:
        manifest = exploration_index.manifest(a)
        assert manifest["format"] == "principia-search-shards/v1"
        assert manifest["total"] == 3
        for item in manifest["shards"]:
            shard = exploration_index.shard(a, item["id"])
            assert shard["snapshot_hash"] == manifest["snapshot_hash"]
            assert digest(shard["payload"].encode()) == item["hash"]
            for row in json.loads(shard["payload"]):
                assert row["compact"] and not row["explanation"]
                full = exploration_index.records(a, [row["id"]])["entries"][0]
                assert (
                    full["content_hash"] == row["content_hash"] and full["explanation"]
                )
        with pytest.raises(ValueError, match="forty"):
            exploration_index.records(a, ["n1"] * 41)
