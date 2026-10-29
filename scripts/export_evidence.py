"""Export pinned flagship maps and dependency-complete briefs for guided reading."""

import argparse
from contextlib import closing
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from principia_legacy.common import write_json
from principia_legacy.storage import Atlas


def run(args):
    with closing(Atlas(args.data_home, args.release)) as atlas:
        if atlas.release == "working":
            raise ValueError("Evidence exports require a frozen release")
        tours = atlas.info()["tours"]
        flagships = ["M06", "P01", "C01", "E01", "B01"]
        topics = sorted(set(flagships) | {id for t in tours for id in t["dossiers"]})
        files = []
        for id in topics:
            brief = atlas.brief("", dossier=id, limit=40)
            nodes = {r["id"]: r for r in brief["relevant_contributions"]}
            sources = {(s["id"], s["revision"]): s for s in brief["sources"]}
            assert brief["permitted_action_scope"] == "read_only"
            for r in brief["supported_relations"]:
                assert all(
                    nodes[p["id"]]["revision"] == p["revision"]
                    for p in [*r["premises"], r["conclusion"]]
                )
            for a in brief["source_anchors"]:
                s = sources[a["source_id"], a["source_revision"]]
                assert any(p["id"] == a["anchor_id"] for p in s["anchors"])
            name = id + "-brief.json"
            write_json(args.output / name, brief)
            files.append(name)
            if id in flagships:
                name = id + "-map.json"
                write_json(
                    args.output / name, atlas.neighborhood(dossier=id, limit=200)
                )
                files.append(name)
        write_json(
            args.output / "index.json",
            {
                "release_id": atlas.release,
                "snapshot_hash": atlas.snapshot_hash,
                "flagships": flagships,
                "tours": tours,
                "files": files,
                "action_scope": "read_only",
                "notice": "Guided comparisons do not assert influence between their topics. Briefs are bounded selections with complete relation endpoints and source anchors; maps contain at most 200 nodes. No human audit is implied.",
            },
        )
        print(
            {
                "briefs": len(topics),
                "flagship_maps": len(flagships),
                "tours": len(tours),
            }
        )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-home", type=Path, required=True)
    p.add_argument("--release", required=True)
    p.add_argument("--output", type=Path, required=True)
    run(p.parse_args())
