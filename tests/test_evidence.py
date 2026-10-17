"""Canonical rechecks must use the exact archived passage, never a later edition."""

import pytest
from principia_legacy.common import digest, write_json
from principia_legacy.evidence import pinned_passages


def test_pinned_evidence_falls_back_to_history_and_rejects_tampering(tmp_path):
    text = "A particular result under explicit assumptions."
    source = {
        "id": "s",
        "revision": 1,
        "title": "Original",
        "url": "https://example.org/work",
        "source_version": "original-bytes",
        "anchors": [{"id": "p1", "text_hash": digest(text.encode())}],
    }
    record = {"anchors": [{"source_id": "s", "source_revision": 1, "anchor_id": "p1"}]}
    versions = {("s", 1): source}
    cache = tmp_path / ".work/sources"
    write_json(
        cache / (digest(source["url"]) + ".json"),
        {
            "bytes_hash": "new-edition",
            "passages": [{"id": "p1", "text": "Changed claim"}],
        },
    )
    with pytest.raises(ValueError, match="version unavailable"):
        pinned_passages(tmp_path, record, versions)
    old = cache / "history/original-bytes.json"
    write_json(
        old, {"bytes_hash": "original-bytes", "passages": [{"id": "p1", "text": text}]}
    )
    assert pinned_passages(tmp_path, record, versions)["s@1:p1"]["text"] == text
    write_json(
        old,
        {
            "bytes_hash": "original-bytes",
            "passages": [{"id": "p1", "text": "Tampered claim"}],
        },
    )
    with pytest.raises(ValueError, match="hash mismatch"):
        pinned_passages(tmp_path, record, versions)
