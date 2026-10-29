"""Freeze the explicit 28 October coverage repair; no generated catalogue padding."""

import argparse
import sys
from copy import deepcopy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from principia_legacy.authoring_store import Commit, recover, writer
from principia_legacy.catalog import contributor_id
from principia_legacy.common import digest, read_json, read_lines

PAPERS = [
    (
        "B3001",
        "w-cunningham-yu-neural-recordings",
        "PMC4433019",
        "Dimensionality reduction for large-scale neural recordings",
        2014,
        ["John P. Cunningham", "Byron M. Yu"],
        [
            "neural state space",
            "neuronal state space",
            "neural manifolds",
            "dimensionality reduction for neural recordings",
        ],
        "A review comparing ways to recover low-dimensional structure from large neural recordings. Distinguish descriptive coordinates, latent-variable assumptions and causal mechanisms.",
    ),
    (
        "B3001",
        "w-churchland-neural-population-dynamics",
        "PMC3393826",
        "Neural population dynamics during reaching",
        2012,
        ["Mark M. Churchland", "John P. Cunningham"],
        [
            "neural population dynamics",
            "motor cortical dynamics",
            "rotational dynamics",
        ],
        "An experimental study of population activity during reaching. Its dynamical interpretation is scoped to the recorded tasks and populations; it does not establish a universal motor-cortex mechanism.",
    ),
    (
        "B3002",
        "w-semedo-communication-subspace",
        "PMC6449210",
        "Cortical areas interact through a communication subspace",
        2019,
        [
            "João D. Semedo",
            "Amin Zandvakili",
            "Christian K. Machens",
            "Byron M. Yu",
            "Adam Kohn",
        ],
        [
            "neural population communication",
            "neuronal population communication",
            "neuronal group communication",
            "interareal communication",
            "communication subspace",
        ],
        "A study of low-dimensional predictive relationships between simultaneously recorded cortical populations. Prediction and shared variability are distinguished from causal transmission and universal routing claims.",
    ),
]

SELECTION = {
    "mathematics": ["M2050", "M2059", "M2106", "M2144", "M2156"],
    "physics": ["P2098", "P2114", "P2138", "P2154", "P2162"],
    "computer_science": ["C2021", "C2045", "C2128", "C2141", "C2169"],
    "economics": ["E2050", "E2060", "E2078", "E2143", "E2188"],
    "biology_medicine": ["B2204", "B2151"],
}


def prepare(root):
    plan_id = "coverage-repair-20261028"
    with writer(root):
        recover(root)
        commit = Commit(root, "prepare:" + plan_id)
        registry = read_lines(root / "manifests/FRONTIER_REGISTRY.jsonl")
        by_id = {d["id"]: d for d in registry}
        if "B3002" not in by_id:
            topic = deepcopy(by_id["B3001"])
            topic.update(
                id="B3002",
                title="Communication between neural populations",
                endpoint=None,
                status="in_progress",
                source_passes=0,
                search_outcomes={
                    "alternatives": "pending",
                    "attribution": "pending",
                    "limitations": "pending",
                },
                area="Neuroscience",
                tags=["neuroscience", "communication subspace", "neural populations"],
                backward_search="Explain shared variability, population states, reduced-rank regression and selective interareal prediction from the actual study.",
                boundary_task="Distinguish observational prediction from causal transmission; preserve species, recording and task limitations.",
                selection_reason="Reported query gap: population-level communication is distinct from single-neuron synaptic transmission.",
                gaps=[
                    "Cross-work ancestry and broader causal validation remain to be assessed."
                ],
                checklist=[
                    {"id": k, "requirement": text, "contributions": []}
                    for k, text in [
                        (
                            "formal",
                            "Explain population states and predictive subspaces",
                        ),
                        (
                            "method",
                            "Connect the observed population activity to the reported communication-subspace result",
                        ),
                        (
                            "limits",
                            "Preserve observational, species, sampling and task boundaries",
                        ),
                    ]
                ],
            )
            registry.append(topic)
            by_id[topic["id"]] = topic
        extra = {w["id"]: w for w in read_json(root / "config/extra_works.json", [])}
        seeds = {p["id"]: p for p in read_json(root / "config/people_seeds.json", [])}
        jobs = []
        for tid, wid, pmc, title, year, names, aliases, summary in PAPERS:
            url = "https://pmc.ncbi.nlm.nih.gov/articles/" + pmc + "/"
            people = []
            for name in names:
                pid = contributor_id(name)
                # These are narrowly sourced research profiles, not invented biographies.
                profile = seeds.setdefault(
                    pid,
                    {
                        "id": pid,
                        "revision": 1,
                        "name": name,
                        "kind": "person",
                        "aliases": [name.replace(".", "")],
                        "subjects": ["biology_medicine"],
                        "biography": f"A researcher credited as a coauthor of {title} ({year}). This profile links the selected work and its explained ideas; it is not a complete career biography.",
                        "bio_sources": [],
                        "selection_reason": "Contributor to a selected primary neuroscience work or methodological review.",
                    },
                )
                provenance = {
                    "url": url,
                    "title": title,
                    "note": "Paper authorship supports this narrow research profile; authorship alone does not establish individual discovery credit.",
                }
                if provenance not in profile["bio_sources"]:
                    profile["bio_sources"].append(provenance)
                people.append(pid)
            old = extra.get(wid, {})
            extra[wid] = {
                **old,
                "id": wid,
                "title": title,
                "kind": "review"
                if "Cunningham" in str(names) and year == 2014
                else "paper",
                "year": year,
                "subjects": ["biology_medicine"],
                "summary": summary,
                "aliases": aliases,
                "people": people,
                "topic_ids": [tid],
                "evidence_source_ids": ["s-" + digest(url)[:16]],
                "source_refs": [],
                "provenance": [
                    {
                        "url": url,
                        "title": title,
                        "note": "Full-text source acquired for passage-grounded extraction; only independently screened insights are attached.",
                    }
                ],
                "representative": True,
            }
            for key in ("revision", "content_hash", "status", "insight_count"):
                extra[wid].pop(key, None)
            jobs.append(
                {
                    "dossier": tid,
                    "url": url,
                    "role": "endpoint",
                    "depth": 0,
                    "need": summary,
                }
            )
        candidates = read_json(root / "config/source_candidates.json")
        for subject, ids in SELECTION.items():
            for tid in ids:
                assert by_id[tid]["pillar"] == subject
                jobs.append(
                    {
                        "dossier": tid,
                        "url": candidates[tid][0],
                        "role": "endpoint",
                        "depth": 0,
                        "need": "Repair an unfinished explanation of "
                        + by_id[tid]["title"]
                        + ". Explain substantive mechanisms, necessary assumptions and limitations. Distinguish exposition from original discovery; reuse supported existing ideas, without padding or inferred historical influence.",
                    }
                )
        plan = {
            "id": plan_id,
            "model": "deepseek-ai/DeepSeek-V4.1-Flash",
            "critic_model": "deepseek-ai/DeepSeek-V4.1-Flash",
            "assignments": jobs,
            "frozen_checklists": {
                j["dossier"]: deepcopy(by_id[j["dossier"]]["checklist"]) for j in jobs
            },
            "rationale": "Twenty-five source assignments, five per subject. Repair actual reading gaps before catalogue growth. The three neuroscience sources answer two reported query gaps. Independent request-level screening is not an independent model or human audit.",
        }
        path = root / "config/plans" / (plan_id + ".json")
        existing = read_json(path)
        if existing and existing != plan:
            raise ValueError("Frozen repair plan differs; use a new identity")
        commit.lines(root / "manifests/FRONTIER_REGISTRY.jsonl", registry)
        commit.json(root / "config/people_seeds.json", list(seeds.values()))
        commit.json(root / "config/extra_works.json", list(extra.values()))
        commit.json(path, plan)
        budget = read_json(root / "config/provider_budget.json")
        budget.update(
            checked_at="2026-10-28",
            inspection_note="User requested substantive coverage repair. Before the 25-source follow-up, ledger exposure was CNY584.08, including CNY50.765 reserved for 104 unresolved attempts and the CNY300 browser hold. Those are retained, not settled or replayed. Current official pricing page inspected: V4.1-Flash peak input CNY2/output CNY8 per million; keep conservative rates and all existing pause thresholds. Limit new work to this frozen repair and evidence/route checks; no unattended broad generation. Model discovery confirmed the exact ID; provider notes say it is served by the 1017 revision.",
        )
        commit.json(root / "config/provider_budget.json", budget)
        commit.publish()
    print({"plan": plan_id, "assignments": len(jobs), "public_activation": False})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-home", type=Path, required=True)
    prepare(parser.parse_args().data_home)
