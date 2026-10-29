"""Optional server-only semantic fallback. No provider requests or query persistence.

The standard-library reader does not import numerical/model dependencies unless a
snapshot-pinned index is explicitly configured. Keyword results retain priority.
"""

import json
import os
from pathlib import Path
from threading import Lock

from .common import digest

MODEL = "sentence-transformers/all-MiniLM-L6-v2"
MIN_SIMILARITY = 0.46  # Development calibration, not a relevance probability.
_cache = None
_lock = Lock()


class SemanticIndex:
    def __init__(self, folder, model_cache):
        import numpy as np
        from fastembed import TextEmbedding

        self.meta = json.loads((folder / "manifest.json").read_text())
        if self.meta["model"] != MODEL:
            raise ValueError("Unsupported semantic model")
        for name in ("entries.json", "vectors.npy"):
            if digest((folder / name).read_bytes()) != self.meta["sha256"][name]:
                raise ValueError("Semantic index checksum mismatch")
        for name, checksum in self.meta.get("model_files", {}).items():
            path = Path(model_cache) / name
            if (
                not path.resolve().is_relative_to(Path(model_cache).resolve())
                or digest(path.read_bytes()) != checksum
            ):
                raise ValueError("Semantic encoder checksum mismatch")
        self.entries = json.loads((folder / "entries.json").read_text())
        self.vectors = np.load(
            folder / "vectors.npy", mmap_mode="r", allow_pickle=False
        )
        if self.vectors.shape != (len(self.entries), 384):
            raise ValueError("Semantic index dimensions mismatch")
        self.model = TextEmbedding(
            MODEL, cache_dir=str(model_cache), local_files_only=True, threads=2
        )
        self.model_lock = Lock()

    def rank(self, query, pillar, human):
        import numpy as np

        with self.model_lock:
            vector = np.asarray(next(self.model.query_embed(query)), dtype=np.float32)
        vector /= max(float(np.linalg.norm(vector)), 1e-9)
        scores = self.vectors @ vector
        # Similarity is a navigation heuristic, never a probability or evidence.
        eligible = [
            (float(scores[i]), item)
            for i, item in enumerate(self.entries)
            if scores[i] >= MIN_SIMILARITY
            and (not pillar or pillar in item["subjects"])
            and (not human or item["human"])
        ]
        eligible.sort(key=lambda pair: (-pair[0], pair[1]["kind"], pair[1]["id"]))
        if not eligible:
            return []
        cutoff = max(MIN_SIMILARITY, eligible[0][0] - 0.13)
        return [(score, item) for score, item in eligible if score >= cutoff][:160]


def load(atlas):
    global _cache
    configured = os.environ.get("PRINCIPIA_SEMANTIC_HOME")
    model_cache = os.environ.get("PRINCIPIA_MODEL_CACHE")
    if not configured or not model_cache:
        return None
    folder = Path(configured).resolve()
    manifest = folder / "manifest.json"
    if not manifest.exists():
        return None
    stat = manifest.stat()
    signature = (str(folder), stat.st_ino, stat.st_mtime_ns, str(model_cache))
    with _lock:
        if not _cache or _cache[0] != signature:
            meta = json.loads(manifest.read_text())
            if meta["snapshot_hash"] != atlas.snapshot_hash:
                return None
            _cache = (signature, SemanticIndex(folder, model_cache))
        index = _cache[1]
    return index if index.meta["snapshot_hash"] == atlas.snapshot_hash else None


def search(atlas, query, pillar, human, offset, limit, signature):
    # A lone name/code or a punctuation-only string should not acquire unrelated
    # neighbours. Existing explicit aliases still handle those keyword searches.
    from .retrieval import STOP, tokens

    if len([word for word in tokens(query) if word not in STOP]) < 2:
        return None
    try:
        index = load(atlas)
        if index is None:
            return None
        matches = index.rank(query, pillar, human)
    except (ImportError, OSError, ValueError, RuntimeError):
        # The optional service cannot make ordinary keyword browsing unavailable.
        return None
    if not matches:
        return None
    grouped = {key: [] for key in ("results", "topics", "works", "people")}
    for score, item in matches:
        grouped[item["kind"]].append(item["id"])
    # One bounded navigation hop exposes the actual checked content of a matched
    # work/topic. Membership is not a claim of entailment or historical influence.
    expanded = []
    for kind, table, owner in [
        ("works", "work_members", "work"),
        ("topics", "topic_members", "topic"),
    ]:
        for id in grouped[kind][:5]:
            for row in atlas.db.execute(
                f"SELECT n.id FROM {table} m JOIN visible_nodes n ON n.snapshot=m.snapshot AND n.id=m.id WHERE m.snapshot=? AND m.{owner}=? AND (? IS NULL OR n.pillar=?) AND (NOT ? OR n.human!='not_reviewed') ORDER BY n.title,n.id LIMIT 8",
                (atlas.release, id, pillar, pillar, human),
            ):
                if row[0] not in grouped["results"]:
                    grouped["results"].append(row[0])
                    expanded.append({"id": row[0], "via_kind": kind, "via_id": id})
        if kind == "works":
            for id in grouped[kind][:5]:
                for (person,) in atlas.db.execute(
                    "SELECT p.id FROM work_people w JOIN people p ON p.snapshot=w.snapshot AND p.id=w.person WHERE w.snapshot=? AND w.work=? AND (? IS NULL OR EXISTS(SELECT 1 FROM catalog_subjects s WHERE s.snapshot=p.snapshot AND s.id=p.id AND s.kind='person' AND s.pillar=?)) AND (NOT ? OR EXISTS(SELECT 1 FROM person_members m JOIN visible_nodes n ON n.snapshot=m.snapshot AND n.id=m.id WHERE m.snapshot=p.snapshot AND m.person=p.id AND n.human!='not_reviewed')) ORDER BY p.id LIMIT 8",
                    (atlas.release, id, pillar, pillar, human),
                ):
                    if person not in grouped["people"]:
                        grouped["people"].append(person)
    output = {}
    for kind, ids in grouped.items():
        page = ids[offset : offset + limit]
        if kind == "results":
            output[kind] = atlas.get_many(page, "contribution")
        else:
            table = "topic_summaries" if kind == "topics" else kind
            marks = ",".join("?" for _ in page)
            values = (
                {
                    row[0]: json.loads(row[1])
                    for row in atlas.db.execute(
                        f"SELECT id,payload FROM {table} WHERE snapshot=? AND id IN ({marks})",
                        (atlas.release, *page),
                    )
                }
                if page
                else {}
            )
            output[kind] = [values[id] for id in page if id in values]
    totals = {
        ("ideas" if k == "results" else k): len(ids) for k, ids in grouped.items()
    }
    return atlas.response(
        **output,
        totals=totals,
        offset=offset,
        limit=limit,
        next_cursor=atlas._next(offset, limit, max(totals.values()), signature),
        search_interpretation={
            "queries": [query],
            "corrections": [],
            "concepts": [],
            "match_mode": "semantic",
            "model": MODEL,
            "membership_expansion": expanded,
            "notice": "Related by meaning. Includes checked insights from matched works and topics. These suggestions do not establish coverage of the full question.",
        },
    )
