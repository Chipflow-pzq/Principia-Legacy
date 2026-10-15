"""Export the public schema contract from the shared field/predicate registries."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from principia_legacy.records import REQUIRED, PREDICATES, PILLARS, KINDS
from principia_legacy.common import write_json

root = Path(__file__).resolve().parents[1]
ref = {
    "type": "object",
    "required": ["id", "revision"],
    "properties": {
        "id": {"type": "string"},
        "revision": {"type": "integer", "minimum": 1},
    },
}
anchor_ref = {
    "type": "object",
    "required": ["source_id", "source_revision", "anchor_id"],
    "properties": {
        "source_id": {"type": "string"},
        "source_revision": {"type": "integer", "minimum": 1},
        "anchor_id": {"type": "string"},
    },
}
for kind, fields in REQUIRED.items():
    properties = {k: {"type": "string"} for k in fields}
    properties.update(
        {
            "id": {"type": "string", "pattern": "^[A-Za-z0-9_-]{1,100}$"},
            "type": {"const": kind},
            "schema_version": {"const": 1},
            "revision": {"type": "integer", "minimum": 1},
            "content_hash": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
        }
    )
    for key in ("assumptions", "limits", "dossiers", "creators"):
        if key in fields:
            properties[key] = {"type": "array", "items": {"type": "string"}}
    for key in ("attribution", "evidence_checked"):
        if key in fields:
            properties[key] = {"type": "array", "items": {"type": "object"}}
    for key in ("curation", "rights", "target"):
        if key in fields:
            properties[key] = {"type": "object"}
    if kind == "contribution":
        properties.update(
            {
                "kind": {"enum": sorted(KINDS)},
                "pillar": {"enum": list(PILLARS)},
                "date": {
                    "type": "object",
                    "required": ["year", "precision", "event", "note"],
                    "properties": {
                        "year": {"type": ["integer", "null"]},
                        "precision": {"type": "string"},
                        "event": {"type": "string"},
                        "note": {"type": "string"},
                    },
                },
            }
        )
    if kind == "relation":
        properties.update(
            {
                "premises": {"type": "array", "minItems": 1, "items": ref},
                "conclusion": ref,
                "premise_mode": {"const": "all"},
                "predicate": {"enum": list(PREDICATES)},
                "layer": {"enum": sorted({v[0] for v in PREDICATES.values()})},
            }
        )
    if "anchors" in fields:
        properties["anchors"] = {
            "type": "array",
            "items": {"type": "object"} if kind == "source" else anchor_ref,
        }
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"urn:principia-legacy:{kind}:1",
        "title": kind.title(),
        "type": "object",
        "required": [
            "id",
            "type",
            "revision",
            "schema_version",
            "content_hash",
            *fields,
        ],
        "properties": properties,
        "additionalProperties": True,
    }
    write_json(root / "schemas" / f"{kind}.schema.json", schema)
write_json(
    root / "schemas/predicates.json",
    {
        k: {"layer": v[0], "symmetric": v[1], "label": v[2]}
        for k, v in PREDICATES.items()
    },
)
