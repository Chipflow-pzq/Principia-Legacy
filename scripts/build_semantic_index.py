"""Optional private-server authoring job; downloads one model, never user queries."""

import argparse
import importlib.metadata
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from principia_legacy.common import digest, now
from principia_legacy.semantic import MODEL
from principia_legacy.storage import Atlas


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-home", type=Path, required=True)
    parser.add_argument("--model-cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Use a new output path; never overwrite an active index")
    import numpy as np
    from fastembed import TextEmbedding

    atlas = Atlas(args.data_home)
    entries = []
    texts = []
    for row in atlas.db.execute(
        "SELECT n.id,n.pillar,n.human,r.payload FROM visible_nodes n JOIN records r ON r.id=n.id AND r.revision=n.revision WHERE n.snapshot=? ORDER BY n.id",
        (atlas.release,),
    ):
        id, pillar, human, payload = row
        r = json.loads(payload)
        entries.append(
            {
                "id": id,
                "kind": "results",
                "subjects": [pillar],
                "human": human != "not_reviewed",
            }
        )
        texts.append((r["title"] + ". " + r["claim"] + " " + r["explanation"])[:1400])
    for kind, table, member, owner in [
        ("topics", "topic_summaries", "topic_members", "topic"),
        ("works", "works", "work_members", "work"),
        ("people", "people", "person_members", "person"),
    ]:
        for id, payload in atlas.db.execute(
            f"SELECT id,payload FROM {table} WHERE snapshot=? ORDER BY id",
            (atlas.release,),
        ):
            r = json.loads(payload)
            human = bool(
                atlas.db.execute(
                    f"SELECT 1 FROM {member} m JOIN visible_nodes n ON n.snapshot=m.snapshot AND n.id=m.id WHERE m.snapshot=? AND m.{owner}=? AND n.human!='not_reviewed' LIMIT 1",
                    (atlas.release, id),
                ).fetchone()
            )
            subjects = (
                [r["pillar"]]
                if kind == "topics"
                else r.get("subjects", r.get("pillars", []))
            )
            entries.append(
                {"id": id, "kind": kind, "subjects": subjects, "human": human}
            )
            texts.append(
                (
                    r.get("title", r.get("name", ""))
                    + ". "
                    + " ".join(r.get("aliases", []))
                    + " "
                    + r.get("summary", r.get("biography", ""))
                    + (" " + r.get("backward_search", "") if kind == "topics" else "")
                )[:1400]
            )
    model = TextEmbedding(MODEL, cache_dir=str(args.model_cache), threads=2)
    vectors = np.asarray(list(model.embed(texts, batch_size=32)), dtype=np.float32)
    vectors /= np.maximum(np.linalg.norm(vectors, axis=1, keepdims=True), 1e-9)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    folder = Path(tempfile.mkdtemp(prefix=".semantic-", dir=args.output.parent))
    try:
        (folder / "entries.json").write_text(json.dumps(entries, separators=(",", ":")))
        np.save(folder / "vectors.npy", vectors, allow_pickle=False)
        manifest = {
            "created_at": now(),
            "release_id": atlas.release,
            "snapshot_hash": atlas.snapshot_hash,
            "model": MODEL,
            "fastembed": importlib.metadata.version("fastembed"),
            "model_files": {
                str(p.relative_to(args.model_cache)): digest(p.read_bytes())
                for p in args.model_cache.rglob("*")
                if p.is_file() and "snapshots" in p.parts and not p.name.startswith(".")
            },
            "dimensions": 384,
            "text_projection_version": 2,
            "entries": len(entries),
            "sha256": {
                name: digest((folder / name).read_bytes())
                for name in ["entries.json", "vectors.npy"]
            },
        }
        (folder / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        folder.rename(args.output)
    finally:
        if folder.exists():
            shutil.rmtree(folder)
        atlas.close()
    print(json.dumps(manifest), flush=True)


if __name__ == "__main__":
    main()
