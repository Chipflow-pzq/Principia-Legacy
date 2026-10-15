"""Verify release-specific integrity against the actual corpus, not sample fixtures."""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from principia_legacy.common import digest, read_json
from principia_legacy.storage import Atlas, corpus
from principia_legacy.records import validate, visible

root = Path(__file__).resolve().parents[1]
records = corpus(root)
errors = validate(records)
if errors:
    raise ValueError(errors[:20])
a = Atlas(root)
latest = a.records
accepted = {
    r["target"]["content_hash"]
    for r in latest
    if r["type"] == "review"
    and r["reviewer_type"] == "machine"
    and r["judgment"] == "accepted"
}
readable = [
    r for r in latest if r["type"] in ("contribution", "relation") and visible(r)
]
assert all(r["content_hash"] in accepted for r in readable), (
    "Machine-screened label needs an exact accepted review"
)
counts = a.info()["counts"]
dossiers = a.dossiers()["dossiers"]
assert len(dossiers) >= 60
assert len({d["id"] for d in dossiers}) == len(dossiers)
assert (
    len({r["id"] for r in readable if r["type"] == "contribution"})
    == counts["contribution"]
)
for d in dossiers:
    assert (
        d["contribution_count"]
        == a.db.execute(
            "SELECT COUNT(*) FROM topic_members WHERE snapshot=? AND topic=?",
            (a.release, d["id"]),
        ).fetchone()[0]
    ), "Topic coverage must count unique admitted members, including shared membership"
for d in dossiers:
    g = a.neighborhood(dossier=d["id"], limit=999)
    assert len(g["contributions"]) <= 200
    ids = {n["id"] for n in g["contributions"]}
    assert all(
        all(x["id"] in ids for x in [*r["premises"], r["conclusion"]])
        for r in g["relations"]
    )
for tour in a.info()["tours"]:
    assert all(id in {d["id"] for d in dossiers} for id in tour["dossiers"])
for d in ["M06", "P01", "C01", "E01", "B01"]:
    assignment = next(x for x in dossiers if x["id"] == d)
    assert assignment["endpoint"]
    a.get(assignment["endpoint"], "contribution")
    brief = a.brief("", dossier=d)
    assert brief["permitted_action_scope"] == "read_only"
    refs = {(s["id"], s["revision"]) for s in brief["sources"]}
    assert all(
        (r["source_id"], r["source_revision"]) in refs for r in brief["source_anchors"]
    )
eval_manifest = read_json(root / "tests/evaluation/manifest.json")
for split in ("dev", "heldout"):
    assert (
        digest((root / "tests/evaluation" / f"{split}.jsonl").read_bytes())
        == eval_manifest[split + "_hash"]
    )
try:
    import jsonschema
except ImportError:
    schema_status = "not run; optional authoring dependency unavailable"
else:
    schemas = {
        name: read_json(root / "schemas" / f"{name}.schema.json")
        for name in ("contribution", "relation", "source", "review")
    }
    for schema in schemas.values():
        jsonschema.Draft202012Validator.check_schema(schema)
    validators = {
        name: jsonschema.Draft202012Validator(schema)
        for name, schema in schemas.items()
    }
    for r in records:
        validators[r["type"]].validate(r)
    schema_status = (
        f"{len(records)} immutable versions validated against exported JSON Schemas"
    )
print(
    json.dumps(
        {
            "passed": True,
            "release_id": a.release,
            "snapshot_hash": digest(a.manifest),
            "counts": counts,
            "exact_machine_reviews_for_all_visible_records": True,
            "dossiers": len(dossiers),
            "flagship_endpoint_checks": 5,
            "tour_checks": 3,
            "source_closure": True,
            "neighborhood_cap_and_joint_premises": True,
            "frozen_evaluation_files_unchanged": True,
            "external_jsonschema": schema_status,
            "qualified_human_audit": "not performed",
        },
        indent=2,
    )
)
a.close()
