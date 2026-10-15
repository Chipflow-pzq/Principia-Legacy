"""Exercise real flagship corrections in a disposable copy; never alter the atlas."""

import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "src"))
from principia_legacy.common import write_json
from principia_legacy.lifecycle import prepare_patch, apply_patch
from principia_legacy.release import freeze
from principia_legacy.storage import Atlas, build

checks = []
with tempfile.TemporaryDirectory(prefix="principia-living-check-") as directory:
    sandbox = Path(directory)
    for folder in ("corpus", "manifests", "tours"):
        shutil.copytree(root / folder, sandbox / folder)
    freeze(sandbox, "living-check-original")
    build(sandbox, "living-check-original")
    a = Atlas(sandbox)
    assignments = {d["id"]: d for d in a.dossiers()["dossiers"]}
    originals = {
        id: a.get(assignments[id]["endpoint"])
        for id in ("M06", "P01", "C01", "E01", "B01")
    }
    a.close()
    for id, original in originals.items():
        candidate = copy.deepcopy(original)
        candidate["revision"] += 1
        candidate["limits"].append(
            "TEST FIXTURE ONLY: proposed scope revision; not a scientific assertion."
        )
        patch = prepare_patch(
            sandbox,
            {
                "reason": "Disposable correction propagation check",
                "base_hashes": {original["id"]: original["content_hash"]},
                "records": [candidate],
            },
        )
        assert patch["impact"], (
            "Flagship endpoint needs an inspectable dependent relation for this check"
        )
        write_json(sandbox / "proposed.json", patch)
        apply_patch(sandbox, sandbox / "proposed.json")
        build(sandbox)
        old = Atlas(sandbox, "living-check-original")
        current = Atlas(sandbox)
        assert old.get(original["id"])["content_hash"] == original["content_hash"]
        try:
            current.get(original["id"])
            raise AssertionError("Unreviewed correction leaked into browsing")
        except KeyError:
            pass
        assert not any(
            n["id"] == original["id"]
            for n in current.brief("", dossier=id)["relevant_contributions"]
        )
        dossier = next(d for d in current.dossiers()["dossiers"] if d["id"] == id)
        assert dossier["status"] != "initial_neighborhood"
        diff = current.changes("living-check-original")
        assert any(x["after"]["id"] == original["id"] for x in diff["changed"])
        for relation_id in patch["impact"]:
            try:
                current.get(relation_id)
                raise AssertionError(
                    "Dependent interpretation escaped recheck quarantine"
                )
            except KeyError:
                pass
        checks.append(
            {
                "dossier": id,
                "target": original["id"],
                "dependent_interpretations": len(patch["impact"]),
                "old_snapshot_preserved": True,
                "new_approval_required": True,
                "coverage_updated": True,
                "brief_updated": True,
            }
        )
        old.close()
        current.close()
print(
    json.dumps(
        {
            "passed": True,
            "scope": "Actual flagship records, isolated disposable corpus copy; no fabricated corrections or human reviews added to distributed corpus",
            "checks": checks,
        },
        indent=2,
    )
)
