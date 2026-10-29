"""Freeze four balanced extensions, registering only assignments actually selected."""

import argparse
from copy import deepcopy
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from principia_legacy.common import read_json, read_lines
from principia_legacy.authoring_store import writer, recover, Commit
from principia_legacy.records import PILLARS
from principia_legacy.retrieval import normalize

# Editorial selection: substantive mechanisms, welfare and market institutions;
# bookkeeping instructions and calculator walkthroughs are not atlas insights.
ECONOMICS = [
    "E2014",
    "E2016",
    "E2018",
    "E2020",
    "E2022",
    "E2026",
    "E2028",
    "E2032",
    "E2034",
    "E2038",
    "E2040",
    "E2044",
    "E2048",
    "E2050",
    "E2056",
    "E2058",
    "E2060",
    "E2074",
    "E2078",
    "E2082",
]


def run(root):
    backlog = read_json(root / "config/foundations-curriculum-1-2-v2.json")
    priority = read_json(root / "config/source-priorities-1.5.json")["subjects"]
    templates = {t["id"]: t for t in backlog["topic_templates"]}
    assignments = {
        j["dossier"]: j for b in backlog["batches"] for j in b["assignments"]
    }
    with writer(root):
        recover(root)
        registry = read_lines(root / "manifests/FRONTIER_REGISTRY.jsonl")
        by_id = {t["id"]: t for t in registry}
        by_title = {(t["pillar"], normalize(t["title"])): t["id"] for t in registry}
        original_plans = [
            read_json(root / "config/plans" / f"foundations-1-5-{i:03}.json")
            for i in range(1, 11)
        ]
        used = {j["dossier"] for plan in original_plans for j in plan["assignments"]}
        chosen = {}
        for pillar in PILLARS:
            candidates = (
                priority[pillar]["selected"]
                if pillar != "economics"
                else [
                    {
                        "id": id,
                        "need": "Explain the scoped economic mechanism, its assumptions and limitations; distinguish textbook exposition from original discovery.",
                        "endpoint": templates[id]["title"],
                    }
                    for id in ECONOMICS
                ]
            )
            jobs = []
            for item in candidates:
                template = templates[item["id"]]
                topic = by_title.get(
                    (pillar, normalize(template["title"])), template["id"]
                )
                if topic in used:
                    continue
                job = {
                    **assignments[item["id"]],
                    "dossier": topic,
                    "need": item["need"]
                    + " Endpoint sought: "
                    + item["endpoint"]
                    + " Preserve independent formulations and do not infer historical priority from this exposition.",
                }
                used.add(topic)
                jobs.append(job)
                if topic not in by_id:
                    new = deepcopy(template)
                    new["selection_reason"] = (
                        "Frozen 1.5 balanced extension; only supported substantive contributions count as coverage."
                    )
                    registry.append(new)
                    by_id[topic] = new
                    by_title[(pillar, normalize(new["title"]))] = topic
                if len(jobs) == 20:
                    break
            if len(jobs) != 20:
                raise ValueError(
                    f"Need 20 selected assignments for {pillar}; found {len(jobs)}"
                )
            chosen[pillar] = jobs
        commit = Commit(root, "freeze-foundation-extensions-1.5")
        for i in range(4):
            id = f"foundations-1-5-{i + 11:03}"
            jobs = [
                j for pillar in PILLARS for j in chosen[pillar][i * 5 : (i + 1) * 5]
            ]
            plan = {
                "id": id,
                "model": "deepseek-ai/DeepSeek-V4.1-Flash",
                "critic_model": "deepseek-ai/DeepSeek-V4-Pro",
                "new_node_allowance": 24,
                "maximum_depth": 6,
                "assignments": jobs,
                "selection": "Balanced extension of the frozen editorial shortlist. Expository works do not establish original attribution. Empty assignments remain gaps.",
                "frozen_checklists": {
                    j["dossier"]: deepcopy(by_id[j["dossier"]]["checklist"])
                    for j in jobs
                },
            }
            path = root / "config/plans" / f"{id}.json"
            old = read_json(path)
            if old and old != plan:
                raise ValueError("Refusing to change a frozen extension")
            commit.json(path, plan)
        commit.lines(root / "manifests/FRONTIER_REGISTRY.jsonl", registry)
        commit.json(
            root / "reports/foundation-extensions-1.5.json",
            {
                "assignments": 100,
                "subjects": {
                    p: [j["dossier"] for j in jobs] for p, jobs in chosen.items()
                },
                "status": "assignments frozen; not completed coverage",
            },
        )
        commit.publish()
        print(
            "Frozen 100 assignments in four balanced batches; registered only assigned topics."
        )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-home", type=Path, required=True)
    run(p.parse_args().data_home)
