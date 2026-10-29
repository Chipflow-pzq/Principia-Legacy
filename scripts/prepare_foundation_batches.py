"""Freeze balanced assignments from an editorial shortlist; no model calls."""

import argparse
from collections import defaultdict, deque
from copy import deepcopy
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from principia_legacy.common import read_json, read_lines
from principia_legacy.authoring_store import writer, recover, Commit
from principia_legacy.records import PILLARS
from principia_legacy.retrieval import normalize


def run(root):
    backlog = read_json(root / "config/foundations-curriculum-1-2-v2.json")
    priorities = read_json(root / "config/source-priorities-1.5.json")["subjects"]
    templates = {t["id"]: t for t in backlog["topic_templates"]}
    assignments = {
        j["dossier"]: j for b in backlog["batches"] for j in b["assignments"]
    }
    with writer(root):
        recover(root)
        registry = read_lines(root / "manifests/FRONTIER_REGISTRY.jsonl")
        by_id = {t["id"]: t for t in registry}
        by_title = {(t["pillar"], normalize(t["title"])): t["id"] for t in registry}
        selected = {}
        for pillar in PILLARS:
            areas = defaultdict(deque)
            used = set()
            for choice in priorities[pillar]["selected"]:
                template = templates[choice["id"]]
                if template["pillar"] != pillar:
                    raise ValueError("Shortlist subject mismatch")
                topic = by_title.get(
                    (pillar, normalize(template["title"])), template["id"]
                )
                if topic in used:
                    continue
                used.add(topic)
                job = {
                    **assignments[choice["id"]],
                    "dossier": topic,
                    "need": choice["need"]
                    + " Endpoint sought: "
                    + choice["endpoint"]
                    + " Distinguish original discovery from this source exposition; do not manufacture priority or routine fragments.",
                }
                if topic not in by_id:
                    new = deepcopy(template)
                    new["selection_reason"] = (
                        "Editorially selected foundational source assignment for 1.5; scientific coverage requires independent passage screening."
                    )
                    registry.append(new)
                    by_id[topic] = new
                    by_title[(pillar, normalize(new["title"]))] = topic
                areas[template.get("area", "Other")].append(job)
            queue = []
            while any(areas.values()):
                for group in areas.values():
                    if group:
                        queue.append(group.popleft())
            selected[pillar] = queue
        count = min(len(jobs) // 5 for jobs in selected.values())
        commit = Commit(root, "freeze-foundation-campaign-1.5")
        plans = []
        for i in range(count):
            jobs = [
                j for pillar in PILLARS for j in selected[pillar][i * 5 : (i + 1) * 5]
            ]
            id = f"foundations-1-5-{i + 1:03}"
            plan = {
                "id": id,
                "model": "deepseek-ai/DeepSeek-V4.1-Flash",
                "critic_model": "deepseek-ai/DeepSeek-V4-Pro",
                "new_node_allowance": 24,
                "maximum_depth": 6,
                "assignments": jobs,
                "selection": "Balanced foundational work passes, diversified by source area. A chapter is exposition, not proof of historical priority. This batch does not establish current frontier completeness.",
                "frozen_checklists": {
                    j["dossier"]: deepcopy(by_id[j["dossier"]]["checklist"])
                    for j in jobs
                },
            }
            path = root / "config/plans" / f"{id}.json"
            old = read_json(path)
            if old and old != plan:
                raise ValueError("Refusing to change a frozen batch")
            commit.json(path, plan)
            plans.append(id)
        commit.lines(root / "manifests/FRONTIER_REGISTRY.jsonl", registry)
        commit.json(
            root / "reports/foundation-campaign-1.5.json",
            {
                "plans": plans,
                "assignments": count * 25,
                "remaining_shortlist": {
                    p: len(v) - count * 5 for p, v in selected.items()
                },
                "coverage_notice": "Registered assignments are not populated topics. Readiness requires supported content, an endpoint, an evidenced route and limitations.",
            },
        )
        commit.publish()
        print({"plans": plans, "assignments": count * 25})


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--data-home", type=Path, required=True)
    run(p.parse_args().data_home)
