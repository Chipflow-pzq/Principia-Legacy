"""Versioned record contracts and cross-record semantic validation."""

import re
from urllib.parse import urlparse
from .common import record_hash

PILLARS = {
    "mathematics": "Mathematics",
    "physics": "Physics",
    "computer_science": "Computer science",
    "economics": "Economics",
    "biology_medicine": "Biology & medicine",
}
PREDICATES = {
    "historical_basis_for": (
        "historical",
        False,
        "historical basis for",
        "Earlier insight -> later insight. Evidence explicitly documents intellectual influence; chronology, citation or resemblance alone is insufficient.",
    ),
    "motivated": (
        "historical",
        False,
        "motivated",
        "An earlier problem, result or limitation -> the later response it explicitly inspired. Requires documented motivation.",
    ),
    "applied_in": (
        "historical",
        False,
        "applied in",
        "A method or insight -> the particular later application that demonstrably uses it. Not an inferred influence or mere component listing.",
    ),
    "independent_formulation_of": (
        "historical",
        True,
        "independent formulation of",
        "Two distinct formulations with evidence of independent discovery. Shared subject matter or different authors is insufficient.",
    ),
    "premise_for": (
        "logical",
        False,
        "premise for",
        "Premise claim(s) -> an inferential conclusion under stated assumptions. Explain the derivation. A system and its components are NOT automatically premises for one another; do not use this for part-whole membership.",
    ),
    "generalized_by": (
        "logical",
        False,
        "generalized by",
        "A scoped result -> a genuinely more general result that contains it as a special case. State the scope and reduction.",
    ),
    "bounded_by": (
        "logical",
        False,
        "bounded by",
        "A claim or method -> the bound, condition or counterexample restricting it. A technique that repairs a limitation is not itself the limiting bound.",
    ),
    "supports": (
        "evidential",
        False,
        "supports",
        "Evidence, observation or argument -> the claim it supports. Do not reverse the arrow: a model is not evidence for its evaluation result.",
    ),
    "challenges": (
        "evidential",
        False,
        "challenges",
        "Counterevidence or counterargument -> the claim or method it challenges. A failed prediction challenges the model, not the reverse.",
    ),
    "analogous_to": (
        "conceptual",
        True,
        "analogous to",
        "A specific structural analogy between two ideas, with its limits stated. Shared task or topic alone is insufficient.",
    ),
    "equivalent_under": (
        "conceptual",
        True,
        "equivalent under",
        "Two formulations shown equivalent under explicit conditions. Similar performance or appearance is insufficient.",
    ),
    "prerequisite_for_reading": (
        "pedagogical",
        False,
        "helps explain",
        "A foundation -> the idea it helps a reader understand. Explicit editorial teaching rationale; this does not assert historical influence or logical necessity.",
    ),
}
KINDS = {
    "theorem",
    "argument",
    "empirical_finding",
    "mechanism",
    "representation",
    "method",
    "heuristic",
    "negative_result",
    "conjecture",
    "question",
    "normative_argument",
}
REQUIRED = {
    "contribution": [
        "title",
        "kind",
        "pillar",
        "claim",
        "problem",
        "conceptual_move",
        "explanation",
        "assumptions",
        "limits",
        "attribution",
        "date",
        "anchors",
        "curation",
        "scientific_standing",
        "publication_state",
        "machine_screening",
        "human_review",
        "dossiers",
    ],
    "relation": [
        "premises",
        "conclusion",
        "premise_mode",
        "predicate",
        "layer",
        "scope",
        "warrant",
        "anchors",
        "publication_state",
        "machine_screening",
        "human_review",
        "curation",
    ],
    "source": [
        "title",
        "creators",
        "url",
        "source_version",
        "retrieved_at",
        "access_state",
        "rights",
        "anchors",
    ],
    "review": [
        "target",
        "reviewer_type",
        "reviewer_identity",
        "scope",
        "judgment",
        "rationale",
        "evidence_checked",
        "time",
    ],
}


def visible(record):
    return (
        record.get("publication_state") in {"exploratory", "reviewed"}
        and record.get("machine_screening") == "passed"
    )


def source_anchor_enrichment(old, new):
    """Only additive locators for identical source bytes preserve prior checks."""
    if not old or not new or old.get("type") != "source" or new.get("type") != "source":
        return False
    ignored = {"revision", "content_hash", "anchors", "change_reason"}
    if {k: v for k, v in old.items() if k not in ignored} != {
        k: v for k, v in new.items() if k not in ignored
    }:
        return False
    anchors = {a["id"]: a for a in new.get("anchors", [])}
    return all(anchors.get(a["id"]) == a for a in old.get("anchors", []))


def validate(records):
    errors = []
    indexed = {}
    if not isinstance(records, list):
        return ["Records must be a list"]
    for r in records:
        if not isinstance(r, dict):
            errors.append("Record must be an object")
            continue
        label = f"{r.get('id', '?')}@{r.get('revision', '?')}"
        kind = r.get("type")
        if not isinstance(kind, str) or kind not in REQUIRED:
            errors.append(f"{label}: unknown record type")
            continue
        for key in [
            "id",
            "revision",
            "schema_version",
            "content_hash",
            *REQUIRED[kind],
        ]:
            if key not in r:
                errors.append(f"{label}: missing {key}")
        if not isinstance(r.get("id"), str) or not re.fullmatch(
            r"[A-Za-z0-9_-]{1,100}", r.get("id", "")
        ):
            errors.append(f"{label}: invalid id")
        if type(r.get("revision")) is not int or r["revision"] < 1:
            errors.append(f"{label}: invalid revision")
        if r.get("schema_version") != 1:
            errors.append(f"{label}: unsupported schema version")
        if r.get("content_hash") != record_hash(r):
            errors.append(f"{label}: content hash mismatch")
        field_types = {
            "anchors": list,
            "assumptions": list,
            "limits": list,
            "attribution": list,
            "dossiers": list,
            "premises": list,
            "conclusion": dict,
            "target": dict,
            "date": dict if kind == "contribution" else str,
            "creators": list,
            "rights": dict,
            "curation": dict,
        }
        for field, expected in field_types.items():
            if field in r and not isinstance(r[field], expected):
                errors.append(f"{label}: invalid type for {field}")
        for field in ("anchors", "premises", "attribution"):
            if (
                field in r
                and isinstance(r[field], list)
                and any(not isinstance(item, dict) for item in r[field])
            ):
                errors.append(f"{label}: {field} entries must be objects")
        for field in ("assumptions", "limits", "dossiers", "creators", "tags"):
            if field in r and (
                not isinstance(r[field], list)
                or any(not isinstance(x, str) for x in r[field])
            ):
                errors.append(f"{label}: {field} must contain strings")
        for field in (
            "url",
            "title",
            "claim",
            "problem",
            "conceptual_move",
            "explanation",
            "predicate",
            "layer",
            "scope",
            "warrant",
            "reviewer_identity",
            "rationale",
        ):
            if field in r and not isinstance(r[field], str):
                errors.append(f"{label}: invalid text field {field}")
        endpoint_refs = []
        if isinstance(r.get("premises"), list):
            endpoint_refs.extend(r["premises"])
        for field in ("conclusion", "target"):
            if field in r:
                endpoint_refs.append(r[field])
        for ref in endpoint_refs:
            if (
                not isinstance(ref, dict)
                or not isinstance(ref.get("id"), str)
                or type(ref.get("revision")) is not int
                or ref["revision"] < 1
            ):
                errors.append(f"{label}: malformed revision reference")
        if isinstance(r.get("anchors"), list):
            for ref in r["anchors"]:
                if not isinstance(ref, dict):
                    continue
                if kind == "source":
                    if not isinstance(ref.get("id"), str):
                        errors.append(f"{label}: malformed source anchor")
                elif (
                    not isinstance(ref.get("source_id"), str)
                    or not isinstance(ref.get("anchor_id"), str)
                    or type(ref.get("source_revision")) is not int
                ):
                    errors.append(f"{label}: malformed anchor reference")
        if kind == "contribution" and isinstance(r.get("date"), dict):
            date = r["date"]
            if date.get("year") is not None and type(date["year"]) is not int:
                errors.append(f"{label}: invalid date year")
            for field in ("precision", "event", "note"):
                if not isinstance(date.get(field), str):
                    errors.append(f"{label}: invalid date {field}")
        if not isinstance(r.get("id"), str) or type(r.get("revision")) is not int:
            continue
        key = (r.get("id"), r.get("revision"))
        if key in indexed:
            errors.append(f"{label}: duplicate identity/revision")
        indexed[key] = r
    if errors:
        return sorted(set(errors))
    seen_symmetric = set()
    for r in records:
        label, kind = r.get("id"), r.get("type")
        if kind == "source":
            parsed = urlparse(r.get("url", ""))
            if (
                parsed.scheme not in {"https", "http"}
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or any(ord(c) < 32 for c in r["url"])
            ):
                errors.append(f"{label}: unsafe source URL")
            anchors = r.get("anchors", [])
            if len({a.get("id") for a in anchors}) != len(anchors):
                errors.append(f"{label}: duplicate anchor id")
            for a in anchors:
                if not a.get("selector") or not a.get("summary"):
                    errors.append(f"{label}: anchor lacks locator/context")
                if a.get("checked") and r.get("access_state") not in {
                    "passage_obtained",
                    "anchor_checked",
                }:
                    errors.append(f"{label}: checked anchor without source access")
        if kind == "contribution":
            if r.get("pillar") not in PILLARS or r.get("kind") not in KINDS:
                errors.append(f"{label}: invalid pillar/kind")
            for k in ("title", "claim", "problem", "conceptual_move", "explanation"):
                if not isinstance(r.get(k), str) or not r[k].strip():
                    errors.append(f"{label}: empty {k}")
            if not isinstance(r.get("assumptions"), list) or not isinstance(
                r.get("limits"), list
            ):
                errors.append(f"{label}: assumptions/limits must be lists")
            if (
                r.get("kind") == "normative_argument"
                and r.get("scientific_standing") != "normative/not empirical"
            ):
                errors.append(f"{label}: normative argument misclassified")
        if kind == "relation":
            pred = PREDICATES.get(r.get("predicate"))
            if not pred or pred[0] != r.get("layer"):
                errors.append(f"{label}: predicate/layer mismatch")
            refs = [*r.get("premises", []), r.get("conclusion", {})]
            if (
                not r.get("premises")
                or r.get("premise_mode") != "all"
                or not r.get("warrant")
                or not r.get("scope")
            ):
                errors.append(f"{label}: missing premises, scope, or warrant")
            if len({x.get("id") for x in refs}) != len(refs):
                errors.append(f"{label}: self/repeated endpoint")
            for ref in refs:
                endpoint = indexed.get((ref.get("id"), ref.get("revision")))
                if not endpoint or endpoint.get("type") != "contribution":
                    errors.append(f"{label}: missing endpoint {ref}")
                elif visible(r) and not visible(endpoint):
                    errors.append(f"{label}: visible edge has hidden endpoint")
            if pred and pred[1]:
                if len(r.get("premises", [])) != 1:
                    errors.append(f"{label}: symmetric relation must be binary")
                key = (
                    r.get("predicate"),
                    tuple(
                        sorted((x.get("id", ""), x.get("revision", 0)) for x in refs)
                    ),
                )
                # Multiple revisions of the same relation are legitimate.
                if key in seen_symmetric:
                    other = [
                        x
                        for x in records
                        if x.get("type") == "relation"
                        and x.get("id") != label
                        and x.get("predicate") == r.get("predicate")
                        and {
                            z.get("id")
                            for z in [*x.get("premises", []), x.get("conclusion", {})]
                        }
                        == {z.get("id") for z in refs}
                    ]
                    if other:
                        errors.append(f"{label}: duplicate symmetric relation")
                seen_symmetric.add(key)
        if kind in {"contribution", "relation"}:
            if visible(r) and not r.get("anchors"):
                errors.append(f"{label}: published record lacks anchors")
            for ref in r.get("anchors", []):
                source = indexed.get((ref.get("source_id"), ref.get("source_revision")))
                anchor = (
                    next(
                        (
                            a
                            for a in source.get("anchors", [])
                            if a["id"] == ref.get("anchor_id")
                        ),
                        None,
                    )
                    if source
                    else None
                )
                if not anchor:
                    errors.append(f"{label}: unresolved source anchor")
                elif visible(r) and not anchor.get("checked"):
                    errors.append(f"{label}: published record has unchecked anchor")
            if r.get("human_review") != "not_reviewed":
                reviews = [
                    v
                    for v in records
                    if v.get("type") == "review"
                    and v.get("reviewer_type") == "human"
                    and v.get("judgment") == "accepted"
                    and v.get("target")
                    == {
                        "id": label,
                        "revision": r.get("revision"),
                        "content_hash": r.get("content_hash"),
                    }
                ]
                if not reviews:
                    errors.append(
                        f"{label}: human-review label without exact human review"
                    )
        if kind == "review":
            target = r.get("target", {})
            item = indexed.get((target.get("id"), target.get("revision")))
            if not item or item.get("content_hash") != target.get("content_hash"):
                errors.append(f"{label}: review target mismatch")
            if r.get("reviewer_type") == "human" and not r.get("human_attestation"):
                errors.append(f"{label}: missing explicit human attestation")
    return sorted(set(errors))
