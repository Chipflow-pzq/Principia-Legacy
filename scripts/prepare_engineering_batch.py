"""Freeze source-complete tasks for important application gaps."""

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from principia_legacy.common import read_lines, read_json
from principia_legacy.authoring_store import writer, recover, Commit

TOPICS = [
    (
        "P1501",
        "Reusable orbital rockets: propulsion, control and recovery",
        "physics",
        [
            (
                "https://www.spacex.com/assets/media/falcon-users-guide-2025-05-09.pdf",
                "endpoint",
                "Distinguish the demonstrated recovery and reuse of Falcon first stages from full-vehicle reuse. Treat vendor performance statements as dated vendor reports, not independent causal proof.",
            ),
            (
                "https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/rocket-thrust-equation/",
                "foundation",
                "Explain momentum flux, pressure thrust and vacuum propulsion from Newtonian mechanics. Do not confuse a force pair with a cancellation of forces on one body.",
            ),
            (
                "https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/ideal-rocket-equation/",
                "foundation",
                "Explain the variable-mass velocity increment and mass-ratio tradeoff, with idealization limits. Relate to reuse only if this source supports the exact statement.",
            ),
        ],
    ),
    (
        "P1502",
        "Chip lithography: resolution, light sources and EUV patterning",
        "physics",
        [
            (
                "https://www.asml.com/en/products/euv-lithography-systems",
                "endpoint",
                "Explain how EUV patterning integrates a short-wavelength source, reflective optics and vacuum. Preserve commercial-source scope and dated performance claims. Component membership is not logical deduction.",
            ),
            (
                "https://www.asml.com/en/technology/lithography-principles/light-and-lasers",
                "foundation",
                "Explain the progression from optical wavelengths to excimer DUV and laser-produced EUV plasma. Do not imply a wavelength alone determines manufactured feature size.",
            ),
        ],
    ),
    (
        "P1503",
        "Plasma-enhanced chemical vapour deposition: activation and film growth",
        "physics",
        [
            (
                "https://pmc.ncbi.nlm.nih.gov/articles/PMC10490058/",
                "foundation",
                "Explain nonequilibrium plasma activation, radical-mediated growth, competing etching and deposition, and substrate-damage limits. This is review exposition; preserve explicit attribution and do not universalize a polymer-specific model.",
            ),
            (
                "https://arxiv.org/html/2603.11416v1",
                "endpoint",
                "Explain the specific atomic-scale SiO2 PECVD mechanisms reported by a machine-learning-potential molecular-dynamics study. Label simulation and preprint scope explicitly; do not present inferred mechanisms as universally experimentally established.",
            ),
        ],
    ),
    (
        "C1501",
        "GPU computing and the CUDA programming model",
        "computer_science",
        [
            (
                "https://docs.nvidia.com/cuda/archive/13.2.2/cuda-programming-guide/01-introduction/programming-model.html",
                "endpoint",
                "Explain data parallel kernels, blocks, grids, synchronization and memory hierarchy, with scheduling and dependence restrictions. Keep version-specific extensions distinct from general CUDA abstractions.",
            ),
            (
                "https://docs.nvidia.com/cuda/cuda-programming-guide/01-introduction/introduction.html",
                "foundation",
                "Explain why throughput-oriented GPU execution differs from low-latency serial CPU execution. State when parallelism helps and where it does not.",
            ),
        ],
    ),
]


def run(root):
    with writer(root):
        recover(root)
        registry = read_lines(root / "manifests/FRONTIER_REGISTRY.jsonl")
        existing = {r["id"] for r in registry}
        jobs, checklists = [], {}
        for id, title, pillar, sources in TOPICS:
            checklist = [
                {"id": key, "requirement": description, "contributions": []}
                for key, description in [
                    ("endpoint", "Resolve the precise implemented outcome and version"),
                    (
                        "foundation",
                        "Explain governing principles and explicit assumptions",
                    ),
                    (
                        "enabling",
                        "Explain enabling conceptual moves with separately checked relations",
                    ),
                    (
                        "limitations",
                        "State limits, alternatives and unresolved ancestry",
                    ),
                ]
            ]
            if id not in existing:
                registry.append(
                    {
                        "id": id,
                        "title": title,
                        "pillar": pillar,
                        "tags": [pillar],
                        "area": "Influential engineering systems",
                        "flagship": False,
                        "endpoint": None,
                        "status": "unresolved",
                        "checklist": checklist,
                        "gaps": ["Source screening and route checking are pending."],
                        "selection_reason": "Addresses a concrete application gap raised by reader exploration and retrieval acceptance.",
                        "backward_search": title,
                        "boundary_task": "Preserve exact technical scope, original attribution and source limitations.",
                        "frontier_open": True,
                        "search_outcomes": {},
                        "source_passes": 0,
                    }
                )
            checklists[id] = checklist
            for url, role, need in sources:
                jobs.append(
                    {
                        "dossier": id,
                        "url": url,
                        "role": role,
                        "depth": 0 if role == "endpoint" else 1,
                        "need": need,
                        "parent": None,
                    }
                )
        plan = {
            "id": "engineering-1-5-001",
            "model": "deepseek-ai/DeepSeek-V4.1-Flash",
            "critic_model": "deepseek-ai/DeepSeek-V4-Pro",
            "new_node_allowance": 45,
            "assignments": jobs,
            "frozen_checklists": checklists,
            "selection": "Primary vendor technical documentation and NASA exposition. Exact evidence checking required; statements about priority or independent performance are not inferred from marketing.",
        }
        path = root / "config/plans/engineering-1-5-001.json"
        old = read_json(path)
        if old and old != plan:
            raise ValueError("Frozen engineering plan changed")
        commit = Commit(root, "freeze-engineering-1.5")
        commit.lines(root / "manifests/FRONTIER_REGISTRY.jsonl", registry)
        commit.json(path, plan)
        commit.publish()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--data-home", type=Path, required=True)
    run(p.parse_args().data_home)
