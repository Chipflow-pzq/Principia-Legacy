"""Explicit correction patches and revision-bound human review."""

from pathlib import Path

from .common import digest, now, read_json, seal, write_json, write_lines
from .records import validate
from .storage import corpus, latest_records, manifest


def impact(root, target, revision=None):
    records = latest_records(corpus(root))
    shared = read_json(Path(root) / "manifests/topic_memberships.json", [])
    result = _impact(records, shared, target, revision)
    affected = set(result["recheck"]) | {target}
    work_ids = {
        m["work_id"]
        for m in read_json(Path(root) / "manifests/work_insights.json", [])
        if m["contribution"]["id"] in affected
        or any(a["source_id"] == target for a in m.get("anchors", []))
    }
    works = read_json(Path(root) / "manifests/works.json", [])
    work_ids.update(
        w["id"]
        for w in works
        if any(s["id"] == target for s in w.get("source_refs", []))
    )
    result["affected_works"] = sorted(work_ids)
    result["affected_dossiers"] = sorted(
        set(result["affected_dossiers"])
        | {t for w in works if w["id"] in work_ids for t in w["topic_ids"]}
    )
    return result


def _impact(records, shared, target, revision=None):
    direct = []
    for r in records:
        if r["type"] == "relation" and any(
            x["id"] == target and (revision is None or x["revision"] == revision)
            for x in [*r["premises"], r["conclusion"]]
        ):
            direct.append(r["id"])
        if r["type"] in ("contribution", "relation") and any(
            a["source_id"] == target
            and (revision is None or a["source_revision"] == revision)
            for a in r.get("anchors", [])
        ):
            direct.append(r["id"])
    affected = set(direct)
    for r in records:
        if r["type"] == "relation" and any(
            x["id"] in affected for x in [*r["premises"], r["conclusion"]]
        ):
            affected.add(r["id"])
    dossiers = sorted(
        {
            d
            for r in records
            if r["id"] in affected | {target}
            for d in r.get("dossiers", [])
        }
    )
    navigation_recheck = [
        m
        for m in shared
        if m["contribution"]["id"] in affected | {target}
        or any(
            a["source_id"] == target
            and (revision is None or a["source_revision"] == revision)
            for a in m.get("anchors", [])
        )
    ]
    dossiers = sorted(set(dossiers) | {m["topic_id"] for m in navigation_recheck})
    return {
        "target": target,
        "revision": revision,
        "direct_dependents": sorted(set(direct)),
        "recheck": sorted(affected),
        "affected_dossiers": dossiers,
        "navigation_recheck": [
            {"topic_id": m["topic_id"], "contribution": m["contribution"]}
            for m in navigation_recheck
        ],
        "policy": "Recheck dependent interpretations; do not automatically reverse conclusions.",
    }


def prepare_patch(root, patch):
    root = Path(root)
    if (
        not patch.get("reason")
        or not isinstance(patch.get("records"), list)
        or not patch["records"]
    ):
        raise ValueError("Patch needs reason and nonempty records")
    existing = corpus(root)
    latest = {r["id"]: r for r in latest_records(existing)}
    shared = read_json(root / "manifests/topic_memberships.json", [])
    changes = []
    affected = set()
    for candidate in patch["records"]:
        r = dict(candidate)
        if r.get("type") == "review":
            raise ValueError("Use the explicit review command for review records")
        old = latest.get(r.get("id"))
        expected = old["revision"] + 1 if old else 1
        if r.get("revision") != expected:
            raise ValueError("Patch revision must be the next revision")
        if old and patch.get("base_hashes", {}).get(old["id"]) != old["content_hash"]:
            raise ValueError("Patch base hash missing or stale")
        if r.get("type") in ("contribution", "relation"):
            r.update(
                publication_state="candidate",
                machine_screening="not_run",
                human_review="not_reviewed",
            )
        r["change_reason"] = patch["reason"]
        seal(r)
        changes.append(r)
        if old and not _source_anchor_enrichment(old, r):
            affected.update(
                _impact(list(latest.values()), shared, old["id"], old["revision"])[
                    "recheck"
                ]
            )
    changed = {r["id"] for r in changes}
    for id in sorted(affected - changed):
        old = latest[id]
        r = dict(old)
        r.update(
            revision=old["revision"] + 1,
            publication_state="quarantined",
            machine_screening="not_run",
            human_review="not_reviewed",
            change_reason="Supporting record changed; requires recheck.",
        )
        seal(r)
        changes.append(r)
    errors = validate([*existing, *changes])
    if errors:
        raise ValueError("\n".join(errors[:30]))
    return {
        "reason": patch["reason"],
        "base_corpus_hash": digest(existing),
        "records": changes,
        "impact": sorted(affected),
        "generated_at": now(),
        "status": "proposed",
    }


def _source_anchor_enrichment(old, new):
    """Adding locators to identical source bytes cannot change older evidence.

    Existing claims continue to pin the old source revision. Any changed source
    metadata, byte version or existing anchor takes the ordinary recheck path.
    """
    if old.get("type") != "source" or new.get("type") != "source":
        return False
    ignored = {"revision", "content_hash", "anchors", "change_reason"}
    if {k: v for k, v in old.items() if k not in ignored} != {
        k: v for k, v in new.items() if k not in ignored
    }:
        return False
    anchors = {a["id"]: a for a in new.get("anchors", [])}
    return all(anchors.get(a["id"]) == a for a in old.get("anchors", []))


def apply_patch(root, patch_path):
    root = Path(root)
    patch = read_json(patch_path)
    if patch.get("status") != "proposed":
        raise ValueError("Apply a patch produced by propose")
    existing = corpus(root)
    if digest(existing) != patch["base_corpus_hash"]:
        raise ValueError("Corpus changed since proposal; regenerate the patch")
    errors = validate([*existing, *patch["records"]])
    if errors:
        raise ValueError("\n".join(errors))
    # Preserve current state before applying; snapshots pin complete revisions.
    before = manifest(root, "before-" + digest(existing)[:12])
    dest = root / "manifests/releases" / (before["release_id"] + ".json")
    if not dest.exists():
        write_json(dest, before)
    patch_id = digest(patch)
    write_lines(root / "corpus/patches" / f"{patch_id}.jsonl", patch["records"])
    write_json(
        root / "manifests/patches" / f"{patch_id}.json",
        {
            "reason": patch["reason"],
            "impact": patch["impact"],
            "applied_at": now(),
            "record_refs": [
                {"id": r["id"], "revision": r["revision"]} for r in patch["records"]
            ],
        },
    )
    return {
        "applied": patch_id,
        "recheck": patch["impact"],
        "previous_release": before["release_id"],
    }


def human_review(
    root,
    target,
    revision,
    reviewer,
    attestation_path,
    scope="editorial",
    judgment="accepted",
):
    if scope not in ("editorial", "domain_expert") or judgment not in (
        "accepted",
        "disputed",
        "rejected",
    ):
        raise ValueError("Invalid review scope/judgment")
    attestation = read_json(attestation_path)
    if (
        attestation.get("reviewer_identity") != reviewer
        or attestation.get("target") != target
        or attestation.get("revision") != revision
        or attestation.get("human_action") is not True
        or not attestation.get("rationale")
    ):
        raise ValueError(
            "Attestation must identify the explicit human action, target, revision, reviewer, and rationale"
        )
    record = next(
        (r for r in corpus(root) if r["id"] == target and r["revision"] == revision),
        None,
    )
    if not record:
        raise ValueError("Review target not found")
    if attestation.get("content_hash") != record["content_hash"]:
        raise ValueError("Attestation hash does not match target")
    r = seal(
        {
            "id": "human-review-" + digest(attestation)[:20],
            "type": "review",
            "schema_version": 1,
            "revision": 1,
            "target": {
                "id": target,
                "revision": revision,
                "content_hash": record["content_hash"],
            },
            "reviewer_type": "human",
            "reviewer_identity": reviewer,
            "scope": scope,
            "judgment": judgment,
            "rationale": attestation["rationale"],
            "evidence_checked": attestation.get("evidence_checked", []),
            "time": now(),
            "human_attestation": attestation,
        }
    )
    dest = Path(root) / "corpus/reviews" / f"{r['id']}.jsonl"
    if dest.exists():
        raise ValueError("This attestation already has a review record")
    write_lines(dest, [r])
    return r
