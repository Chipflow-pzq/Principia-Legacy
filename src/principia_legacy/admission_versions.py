"""Extend source evidence without rewriting admitted scientific records.

Repeated extraction is not a correction. Existing insight and relationship
identities are retained; a differing interpretation requires an explicit patch.
New source anchors receive an immutable source revision and new review pins.
"""

from copy import deepcopy
from .common import digest, seal
from .records import visible


def occurrence_key(record):
    """A conservative duplicate flag, never an automatic identity merge.

    Preserve case and mathematical punctuation. Distinct credited formulators,
    dates and source works remain distinct even when the wording is identical.
    A different title alone cannot turn the same attributed claim into a new idea.
    """
    if record["type"] != "contribution":
        return None
    return digest(
        {
            "claim": " ".join(record["claim"].split()),
            "sources": sorted({a["source_id"] for a in record["anchors"]}),
            "credit": sorted((a["name"], a["role"]) for a in record["attribution"]),
            "date": record.get("date"),
        }
    )


def prepare_versions(existing, records, memberships=()):
    latest = {}
    for record in existing:
        if record["revision"] > latest.get(record["id"], {}).get("revision", 0):
            latest[record["id"]] = record
    records, memberships = deepcopy(records), deepcopy(list(memberships))
    occurrences = {
        occurrence_key(r): r["id"]
        for r in latest.values()
        if r["type"] == "contribution" and visible(r)
    }
    source_pins, additions, withheld = {}, [], []
    for source in (r for r in records if r["type"] == "source"):
        previous = latest.get(source["id"])
        if not previous:
            additions.append(source)
            continue
        old_anchors = {a["id"]: a for a in previous["anchors"]}
        same_version = previous["source_version"] == source["source_version"]
        compatible = same_version and all(
            a["id"] not in old_anchors
            or old_anchors[a["id"]].get("text_hash") == a.get("text_hash")
            for a in source["anchors"]
        )
        if compatible:
            missing = [a for a in source["anchors"] if a["id"] not in old_anchors]
            if missing:
                extended = deepcopy(previous)
                extended.update(
                    revision=previous["revision"] + 1,
                    anchors=[*previous["anchors"], *missing],
                )
                seal(extended)
                additions.append(extended)
            else:
                extended = previous
        else:
            # A new document version gets its own anchors. Older exact pins remain valid.
            extended = {**source, "revision": previous["revision"] + 1}
            seal(extended)
            additions.append(extended)
        source_pins[(source["id"], source["revision"])] = extended["revision"]

    def repin(anchors):
        for anchor in anchors:
            key = (anchor["source_id"], anchor["source_revision"])
            anchor["source_revision"] = source_pins.get(key, anchor["source_revision"])

    for membership in memberships:
        repin(membership["anchors"])
    targets = {}
    for record in records:
        if record["type"] not in ("contribution", "relation"):
            continue
        if record["id"] in latest:
            if record["content_hash"] != latest[record["id"]]["content_hash"]:
                withheld.append(
                    {
                        "id": record["id"],
                        "reason": "Existing identity retained. Changes require an explicit correction patch.",
                    }
                )
            continue
        occurrence = occurrence_key(record)
        if occurrence is not None:
            previous_id = occurrences.get(occurrence)
            if previous_id and previous_id != record["id"]:
                withheld.append(
                    {
                        "id": record["id"],
                        "possible_duplicate_of": previous_id,
                        "reason": "Same attributed claim in the same source work. Review for explicit reuse or a correction; no identity or relation was merged.",
                    }
                )
                continue
            occurrences[occurrence] = record["id"]
        repin(record["anchors"])
        seal(record)
        targets[record["id"]] = record
        additions.append(record)
    # Do not let a rejected collision silently substitute a different endpoint revision.
    collisions = {item["id"] for item in withheld}
    blocked = {
        r["id"]
        for r in additions
        if r["type"] == "relation"
        and any(ref["id"] in collisions for ref in [*r["premises"], r["conclusion"]])
    }
    additions = [r for r in additions if r["id"] not in blocked]
    for record in records:
        if record["type"] != "review":
            continue
        target = targets.get(record["target"]["id"])
        if not target or target["id"] in blocked:
            continue
        repin(record["evidence_checked"])
        record["target"] = {k: target[k] for k in ("id", "revision", "content_hash")}
        record["id"] = (
            "review-" + digest({"prior": record["id"], "target": record["target"]})[:20]
        )
        seal(record)
        additions.append(record)
    withheld.extend(
        {"id": id, "reason": "Endpoint collision requires an explicit correction."}
        for id in sorted(blocked)
    )
    return additions, memberships, withheld
