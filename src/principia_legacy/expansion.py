"""Bounded, resumable source assignments with append-only corpus admission.

An assignment is a research task, never an asserted historical relationship.
The source extractor and independent critic remain the only admission path.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import json

from .common import digest, now, read_json, read_lines, write_json
from .curate import process_source
from .records import validate, visible
from .storage import corpus, latest_records


def _indexed_candidates(root, queries, dossier=None):
    """Bounded hints from the last compiled snapshot, checked again before reuse."""
    from contextlib import closing
    from .storage import Atlas

    if not (Path(root) / "build/atlas.sqlite").exists():
        return None
    selected = {}
    with closing(Atlas(root)) as reader:
        if dossier:
            for n in reader.topic_contributions(dossier, limit=40)["contributions"]:
                selected[n["id"]] = n
        for query in queries[:24]:
            for n in reader.search(query[:500], limit=12, match_any=True)["results"]:
                selected[n["id"]] = n
    return list(selected.values())[:120]


def nearby_contributions(root, dossier):
    """Bounded deduplication hints, never new evidence or automatic identity merges."""
    import re

    terms = set(
        re.findall(
            r"[a-z]{4,}", (dossier["title"] + " " + dossier.get("area", "")).lower()
        )
    )
    try:
        nodes = _indexed_candidates(root, [dossier["title"]], dossier["id"])
    except KeyError:
        nodes = _indexed_candidates(root, [dossier["title"]])
    if nodes is None:
        nodes = [
            n
            for n in latest_records(corpus(root))
            if n["type"] == "contribution" and visible(n)
        ]

    def score(n):
        return (100 if dossier["id"] in n["dossiers"] else 0) + len(
            terms
            & set(re.findall(r"[a-z]{4,}", (n["title"] + " " + n["claim"]).lower()))
        )

    ranked = sorted(((score(n), n) for n in nodes), key=lambda x: (-x[0], x[1]["id"]))
    return [
        {
            k: n[k]
            for k in (
                "id",
                "revision",
                "content_hash",
                "title",
                "claim",
                "attribution",
                "dossiers",
                "assumptions",
                "limits",
                "date",
            )
        }
        for value, n in ranked[:60]
        if value > 0
    ]


def candidate_reuse_hints(root, candidates):
    """Retrieve against actual extracted moves, not just a broad chapter title.

    Similarity only selects evidence-checking candidates. It cannot merge records.
    """
    import re

    stop = {
        "this",
        "that",
        "with",
        "from",
        "which",
        "their",
        "have",
        "when",
        "into",
        "under",
        "method",
        "theory",
        "using",
        "based",
        "through",
        "result",
    }

    def terms(value):
        return set(re.findall(r"[a-z]{4,}", value.lower())) - stop

    nodes = _indexed_candidates(root, [c.get("title", "") for c in candidates])
    if nodes is None:
        nodes = [
            n
            for n in latest_records(corpus(root))
            if n["type"] == "contribution" and visible(n)
        ]
    ranked = {}
    for c in candidates:
        title = terms(c.get("title", ""))
        words = title | terms(c.get("claim", ""))
        matches = []
        for n in nodes:
            nt = terms(n["title"])
            nw = nt | terms(n["claim"])
            overlap = len(words & nw) / max(1, len(words | nw))
            if len(title & nt) >= 2 and overlap >= 0.24:
                matches.append((overlap + len(title & nt) / max(1, len(title | nt)), n))
        for score, n in sorted(matches, key=lambda item: (-item[0], item[1]["id"]))[:2]:
            ranked[n["id"]] = (max(score, ranked.get(n["id"], (0,))[0]), n)
    return [
        {
            k: n[k]
            for k in (
                "id",
                "revision",
                "content_hash",
                "title",
                "claim",
                "attribution",
                "date",
                "assumptions",
                "limits",
                "dossiers",
            )
        }
        for score, n in sorted(
            ranked.values(), key=lambda item: (-item[0], item[1]["id"])
        )[:32]
    ]


def validate_plan(plan, registry):
    if not isinstance(plan.get("id"), str) or not plan["id"].replace("-", "").isalnum():
        raise ValueError("Plan needs a simple stable identity")
    assignments = plan.get("assignments", [])
    seen = set()
    for job in assignments:
        key = (job["dossier"], job["url"])
        if key in seen or job["dossier"] not in registry:
            raise ValueError("Duplicate assignment or unknown dossier")
        seen.add(key)
        depth = job.get("depth", 0)
        if type(depth) is not int or depth < 0 or depth > 10:
            raise ValueError("Depth must be between zero and ten")
        if depth > 6 and not job.get("extension_reason", "").strip():
            raise ValueError("Depth beyond six needs a recorded explanatory need")
        if not job.get("need", "").strip() or not job.get("role"):
            raise ValueError("Every source assignment needs an explanatory purpose")
        if not job["url"].startswith("https://"):
            raise ValueError("Source assignments require public HTTPS")
        if job["dossier"] not in plan.get("frozen_checklists", {}):
            raise ValueError("Freeze the explanatory checklist before expansion")
    return assignments


def admit(root, plan, outcomes):
    from .authoring_store import writer, recover, Commit

    with writer(root):
        recover(root)
        commit = Commit(root, "admit:" + plan["id"])
        result = _admit(root, plan, outcomes, commit)
        commit.publish()
        return result


def _admit(root, plan, outcomes, commit):
    """Never mutate an existing record version or remove frozen source evidence."""
    root = Path(root)
    existing = corpus(root)
    indexed = {(r["id"], r["revision"]): r for r in existing}
    additions = []
    exclusions = read_json(root / "config/admission_exclusions.json", {})
    output = root / "corpus/expansions" / (plan["id"] + ".jsonl")
    prior_admissions = read_lines(output)
    new_per_dossier = {}
    for record in prior_admissions:
        if record["type"] == "contribution":
            for id in record.get("dossiers", []):
                new_per_dossier[id] = new_per_dossier.get(id, 0) + 1
    for outcome in outcomes:
        if outcome.get("state") != "succeeded":
            continue
        result = outcome["result"]
        from .admission_versions import prepare_versions

        records, memberships, withheld = prepare_versions(
            [*existing, *additions],
            result["records"],
            result.get("reused_memberships", []),
        )
        result["reused_memberships"] = memberships
        outcome["retained_existing_identities"] = withheld
        if (
            withheld
            and not memberships
            and not any(r["type"] in ("contribution", "relation") for r in records)
        ):
            outcome["admission"] = "needs_revision_patch"
            outcome["conflicts"] = [item["id"] for item in withheld]
            continue
        conflict = [
            r["id"]
            for r in records
            if (r["id"], r["revision"]) in indexed
            and indexed[(r["id"], r["revision"])]["content_hash"] != r["content_hash"]
        ]
        if conflict:
            outcome["admission"] = "needs_revision_patch"
            outcome["conflicts"] = conflict
            continue
        blocked = set(exclusions)
        blocked.update(
            r["id"]
            for r in records
            if r["type"] == "relation"
            and any(p["id"] in blocked for p in [*r["premises"], r["conclusion"]])
        )
        pending = [
            r
            for r in records
            if (r["id"], r["revision"]) not in indexed
            and r["id"] not in blocked
            and not (r["type"] == "review" and r["target"]["id"] in blocked)
        ]
        count = sum(r["type"] == "contribution" for r in pending)
        dossier = outcome["dossier"]
        if count + new_per_dossier.get(dossier, 0) > plan.get("new_node_allowance", 45):
            outcome["admission"] = "stopped_at_expansion_allowance"
            continue
        errors = validate([*existing, *additions, *pending])
        if errors:
            outcome["admission"] = "quarantined"
            outcome["errors"] = errors[:20]
            continue
        new_per_dossier[dossier] = new_per_dossier.get(dossier, 0) + count
        additions.extend(pending)
        for r in pending:
            indexed[(r["id"], r["revision"])] = r
        outcome["admission"] = "admitted" if pending else "already_documented"
        outcome["new_contributions"] = count
    commit.lines(output, [*prior_admissions, *additions])
    current = [r for r in latest_records([*existing, *additions]) if visible(r)]
    nodes = [r for r in current if r["type"] == "contribution"]
    memberships = read_json(root / "manifests/topic_memberships.json", [])
    by_node = {n["id"]: n for n in nodes}
    keyed = {(m["topic_id"], m["contribution"]["id"]): m for m in memberships}
    for outcome in outcomes:
        if outcome.get("admission") not in {"admitted", "already_documented"}:
            continue
        for membership in outcome["result"].get("reused_memberships", []):
            ref = membership["contribution"]
            n = by_node.get(ref["id"])
            if n and all(n[k] == ref[k] for k in ("id", "revision", "content_hash")):
                keyed[(outcome["dossier"], n["id"])] = {
                    **membership,
                    "topic_id": outcome["dossier"],
                }
    commit.json(root / "manifests/topic_memberships.json", list(keyed.values()))
    registry = read_lines(root / "manifests/FRONTIER_REGISTRY.jsonl")
    registered = {d["id"] for d in registry}
    registry.extend(
        d for d in plan.get("topic_templates", []) if d["id"] not in registered
    )
    fixed = read_json(root / "config/flagship_endpoints.json", {})
    for d in registry:
        good = [
            o["result"]
            for o in outcomes
            if o["dossier"] == d["id"]
            and o.get("admission") in {"admitted", "already_documented"}
        ]
        if not good:
            continue
        members = {n["id"] for n in nodes if d["id"] in n["dossiers"]} | {
            id for topic, id in keyed if topic == d["id"] and id in by_node
        }
        if d["id"] not in fixed and d.get("endpoint") not in members:
            endpoint_results = [
                o["result"]
                for o in outcomes
                if o["dossier"] == d["id"]
                and o.get("role") == "endpoint"
                and o.get("admission") in {"admitted", "already_documented"}
            ]
            d["endpoint"] = next(
                (
                    n
                    for r in endpoint_results
                    for n in r.get("endpoints", [])
                    if n in members
                ),
                None,
            )
        for check in d["checklist"]:
            check["contributions"] = sorted(
                set(check.get("contributions", [])) & members
                | {
                    n
                    for r in good
                    for n, roles in r.get("roles", {}).items()
                    if check["id"] in roles and n in members
                }
            )
        old = d.get("search_outcomes", {})
        d["search_outcomes"] = {
            k: " | ".join(
                dict.fromkeys(
                    [
                        old.get(k, ""),
                        *[r.get("search_outcomes", {}).get(k, "") for r in good],
                    ]
                )
            )
            for k in ("alternatives", "limitations", "attribution")
        }
        gaps = [g for r in good for g in r.get("gaps", [])]
        d["gaps"] = list(dict.fromkeys([*d.get("gaps", []), *gaps]))
        if members:
            d["gaps"] = [
                g
                for g in d["gaps"]
                if g
                not in {
                    "No contributions have passed source-grounded screening yet.",
                    "Source screening is pending.",
                }
            ]
        if d.get("endpoint"):
            d["gaps"] = [
                g
                for g in d["gaps"]
                if g != "Precise frontier endpoint remains unresolved."
            ]
        d["status"] = (
            "initial_neighborhood"
            if len(members) >= 8 and d.get("endpoint")
            else "in_progress"
        )
        d["source_passes"] = len(
            {a["source_id"] for n in nodes if n["id"] in members for a in n["anchors"]}
        )
        d["frontier_open"] = True
    commit.lines(root / "manifests/FRONTIER_REGISTRY.jsonl", registry)
    total = [*prior_admissions, *additions]
    return {
        "new_records": len(additions),
        "new_contributions": sum(r["type"] == "contribution" for r in additions),
        "new_relations": sum(r["type"] == "relation" for r in additions),
        "plan_total_contributions": sum(r["type"] == "contribution" for r in total),
        "plan_total_relations": sum(r["type"] == "relation" for r in total),
    }


def expand(root, plan_path, env_file=None, workers=4):
    root = Path(root)
    plan = read_json(plan_path)
    registry = {
        d["id"]: d for d in read_lines(root / "manifests/FRONTIER_REGISTRY.jsonl")
    }
    jobs = validate_plan(plan, registry)
    plan_hash = digest(plan)
    saved = root / ".work/expansion" / (plan["id"] + ".json")
    public_path = root / "reports/expansion" / (plan["id"] + ".json")
    old = read_json(saved, {}) or read_json(public_path, {})
    if old and old.get("plan_hash") != plan_hash:
        raise ValueError("An executed plan is frozen; use a new plan identity")
    if old.get("completed_at"):
        if not (root / "corpus/expansions" / (plan["id"] + ".jsonl")).exists():
            raise ValueError(
                "Completed batch corpus is missing; restore the archive before authoring"
            )
        return read_json(public_path) or old
    outcomes = {o["assignment_id"]: o for o in old.get("outcomes", [])}
    # Public source allowlist remains explicit and inspectable.
    from .authoring_store import writer, recover, Commit

    with writer(root):
        recover(root)
        candidates = read_json(root / "config/source_candidates.json", {})
        for j in jobs:
            candidates.setdefault(j["dossier"], [])
            if j["url"] not in candidates[j["dossier"]]:
                candidates[j["dossier"]].append(j["url"])
        commit = Commit(root, "source-assignments:" + plan["id"])
        commit.json(root / "config/source_candidates.json", candidates)
        commit.publish()
    receipt = {
        "plan_id": plan["id"],
        "plan_hash": plan_hash,
        "started_at": old.get("started_at", now()),
        "model": plan.get("model", "deepseek-ai/DeepSeek-V4-Flash"),
        "estimate": {
            "assignments": len(jobs),
            "normal_calls_before_retries": len(jobs) * 2,
            "optional_reuse_refinement_calls": len(jobs),
            "maximum_parallel_requests": min(max(workers, 1), 4),
            "maximum_output_tokens_before_retries": len(jobs) * 57344,
            "notice": "Ceilings, not a bill. Interrupted requests may be charged.",
        },
    }
    print(json.dumps({"plan": plan["id"], **receipt["estimate"]}), flush=True)

    def run(j):
        key = digest(j)
        if outcomes.get(key, {}).get("state") in {"succeeded", "abstained"}:
            return outcomes[key]
        d = dict(registry[j["dossier"]])
        d["assignment"] = j
        d["documented_contributions"] = nearby_contributions(root, d)
        try:
            result = process_source(
                root,
                d,
                j["url"],
                env_file,
                receipt["model"],
                critic_model=plan.get("critic_model"),
            )
            return {
                "assignment_id": key,
                **j,
                "state": result["state"],
                "result": result,
            }
        except Exception as e:
            return {
                "assignment_id": key,
                **j,
                "state": "failed",
                "error": str(e)[:300],
                "time": now(),
            }

    with ThreadPoolExecutor(max_workers=min(max(workers, 1), 4)) as pool:
        futures = [pool.submit(run, j) for j in jobs]
        for future in as_completed(futures):
            outcome = future.result()
            previous = outcomes.get(outcome["assignment_id"])
            if previous and previous.get("state") not in {"succeeded", "abstained"}:
                outcome["previous_attempts"] = [
                    *previous.get("previous_attempts", []),
                    {
                        k: v
                        for k, v in previous.items()
                        if k not in {"result", "previous_attempts"}
                    },
                ]
            outcomes[outcome["assignment_id"]] = outcome
            receipt["outcomes"] = list(outcomes.values())
            write_json(saved, receipt)
            print(
                json.dumps(
                    {
                        "dossier": outcome["dossier"],
                        "state": outcome["state"],
                        "screened": outcome.get("result", {}).get("screened"),
                        "error": outcome.get("error"),
                    }
                ),
                flush=True,
            )
    # Admission order follows the frozen plan, independent of request completion order.
    receipt["outcomes"] = [outcomes[digest(j)] for j in jobs]
    receipt["admission"] = admit(root, plan, receipt["outcomes"])
    receipt["completed_at"] = now()
    write_json(saved, receipt)
    public = {
        **receipt,
        "outcomes": [
            {
                **{k: v for k, v in o.items() if k != "result"},
                **{
                    k: v
                    for k, v in o.get("result", {}).items()
                    if k
                    in {
                        "screened",
                        "source_title",
                        "search_outcomes",
                        "gaps",
                        "reuse_refinement",
                        "reused_memberships",
                        "reason",
                    }
                },
            }
            for o in receipt["outcomes"]
        ],
    }
    write_json(public_path, public)
    return public
