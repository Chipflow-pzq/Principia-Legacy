"""Bounded independent checks using exact cited passages and nearby context."""

from .common import digest, now
from .records import PREDICATES


def check_candidates(
    provider, prompt, dossier, passages, contributions, relations, reuse, existing
):
    """A failed check withholds only its batch; completed checks remain resumable.

    Large source chapters must not be retransmitted for every verdict. The
    extractor's exact cited paragraphs remain intact, with adjacent context.
    No truncation, guessed evidence or automatic replay of uncertain requests.
    """
    output = {"contributions": [], "relations": [], "reuse": []}
    receipts, failures, relevance = [], [], []
    by_passage = {p["id"]: i for i, p in enumerate(passages)}
    by_node = {c["local_id"]: c for c in contributions}
    by_node.update({c["id"]: c for c in existing})
    for kind, cases in [
        ("contributions", contributions),
        ("reuse", reuse),
        ("relations", relations),
    ]:
        size = 4 if kind == "relations" else 5
        for offset in range(0, len(cases), size):
            batch = cases[offset : offset + size]
            required = {pid for case in batch for pid in case.get("passage_ids", [])}
            endpoints = {
                id
                for case in batch
                for id in [*case.get("from", []), case.get("to")]
                if id
            }
            indexes = {by_passage[pid] for pid in required if pid in by_passage}
            # Include neighboring context to expose qualifications, without cutting an equation.
            selected = set(indexes)
            used = sum(len(passages[i]["text"]) for i in selected)
            for i in sorted(
                {j for index in indexes for j in (index - 1, index + 1)} | {0, 1}
            ):
                if (
                    0 <= i < len(passages)
                    and i not in selected
                    and used + len(passages[i]["text"]) <= 36000
                ):
                    selected.add(i)
                    used += len(passages[i]["text"])
            payload = {
                "dossier": dossier,
                "passages": [passages[i] for i in sorted(selected)],
                "contributions": batch if kind == "contributions" else [],
                "relations": batch if kind == "relations" else [],
                "reuse": batch if kind == "reuse" else [],
                "endpoint_contributions": [
                    by_node[id] for id in sorted(endpoints) if id in by_node
                ],
                "existing_contributions": [
                    c
                    for c in existing
                    if kind == "reuse" and c["id"] in {v["id"] for v in batch}
                ],
                "check_scope": "Check the supplied cases only. endpoint_contributions identify exact local or reused endpoints; they are untrusted claims, not source evidence.",
            }
            if kind == "relations":
                payload["predicate_meanings"] = {
                    name: {
                        "layer": value[0],
                        "symmetric": value[1],
                        "meaning": value[3],
                    }
                    for name, value in PREDICATES.items()
                    if name in {case.get("predicate") for case in batch}
                }
            field = "local_id" if kind == "contributions" else "index"
            expected = (
                [c["local_id"] for c in batch]
                if field == "local_id"
                else list(range(len(batch)))
            )
            receipt = None
            try:
                if used > 48000 or len(indexes) != len(required):
                    raise ValueError(
                        "Required exact evidence does not fit the bounded critic packet"
                    )
                key = digest(payload)[:24]
                for repair in range(2):
                    requested = (
                        payload
                        if not repair
                        else {
                            **payload,
                            "format_correction": {
                                "required_field": kind,
                                "identities": expected,
                                "identity_field": field,
                            },
                        }
                    )
                    value, receipt = provider.complete(
                        prompt,
                        requested,
                        f"bounded-critic-v1:{kind}:{key}:{repair}",
                        4096,
                    )
                    checks = value.get(kind, [])
                    if (
                        isinstance(value.get("source_relevant"), bool)
                        and isinstance(checks, list)
                        and len(checks) == len(expected)
                        and {c.get(field) for c in checks} == set(expected)
                        and all(
                            c.get("decision")
                            in {"supported", "unsupported", "insufficient_context"}
                            and c.get("rationale", "").strip()
                            for c in checks
                        )
                    ):
                        break
                else:
                    raise ValueError(
                        "Critic omitted exact verdicts after one bounded format repair"
                    )
                relevance.append(value["source_relevant"])
                receipts.append(receipt)
                for check in checks:
                    if field == "index":
                        check["index"] += offset
                    output[kind].append({**check, "receipt": receipt})
            except Exception as exc:
                reason = str(exc)[:300]
                failures.append({"kind": kind, "offset": offset, "reason": reason})
                output[kind].extend(
                    {
                        field: id if field == "local_id" else id + offset,
                        "decision": "insufficient_context",
                        "rationale": "Independent check unfinished: " + reason,
                    }
                    for id in expected
                )
    output["source_relevant"] = bool(relevance) and all(relevance)
    output["failures"] = failures
    summary = {
        "provider": "SiliconFlow",
        "requested_model": provider.model,
        "returned_model": provider.model,
        "request_id": "check-bundle-"
        + digest([r.get("request_id") for r in receipts])[:24],
        "time": now(),
        "method": "bounded independent verdicts; individual receipts attached to accepted checks",
        "batch_receipts": [r["trace_id"] for r in receipts if r.get("trace_id")],
    }
    return output, summary
