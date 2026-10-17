"""Resolve exact, private source passages for reproducible authoring checks."""

from pathlib import Path
from .common import digest, read_json


def pinned_passages(root, record, versions):
    evidence = {}
    for ref in record.get("anchors", []):
        source = versions[(ref["source_id"], ref["source_revision"])]
        cache = read_json(
            Path(root) / ".work/sources" / (digest(source["url"]) + ".json"), {}
        )
        if cache.get("bytes_hash") != source["source_version"]:
            cache = read_json(
                Path(root)
                / ".work/sources/history"
                / (source["source_version"] + ".json"),
                {},
            )
        if cache.get("bytes_hash") != source["source_version"]:
            raise ValueError("Pinned source version unavailable")
        anchor = next(a for a in source["anchors"] if a["id"] == ref["anchor_id"])
        passage = next(p for p in cache["passages"] if p["id"] == ref["anchor_id"])
        if digest(passage["text"].encode()) != anchor["text_hash"]:
            raise ValueError("Pinned passage hash mismatch")
        key = f"{source['id']}@{source['revision']}:{ref['anchor_id']}"
        evidence[key] = {
            "title": source["title"],
            "url": source["url"],
            "reference": ref,
            "text": passage["text"],
        }
    if not evidence:
        raise ValueError("No claim-level source passages")
    return evidence
