"""Report catalog breadth separately from passage-grounded scientific coverage."""

import json
import sys
from collections import Counter
from contextlib import closing
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from principia_legacy.common import write_json
from principia_legacy.records import PILLARS
from principia_legacy.storage import Atlas

root = Path(__file__).resolve().parents[1]
with closing(Atlas(root)) as atlas:
    topics = atlas.dossiers()["dossiers"]
    works = [
        json.loads(r[0])
        for r in atlas.db.execute(
            "SELECT payload FROM works WHERE snapshot=?", (atlas.release,)
        )
    ]
    people = [
        json.loads(r[0])
        for r in atlas.db.execute(
            "SELECT payload FROM people WHERE snapshot=?", (atlas.release,)
        )
    ]
    subjects = {}
    for subject in PILLARS:
        ws = [w for w in works if subject in w["subjects"]]
        ps = [p for p in people if subject in p["subjects"]]
        ts = [t for t in topics if t["pillar"] == subject]
        subjects[subject] = {
            "catalogued_works": len(ws),
            "selected_people": len(ps),
            "works_with_extracted_insights": sum(w["insight_count"] > 0 for w in ws),
            "registered_topics": len(ts),
            "populated_topics": sum(t["contribution_count"] > 0 for t in ts),
            "unique_primary_subject_insights": atlas.info()["subject_counts"][subject],
            "catalog_shortfall_to_suggested_200_works": max(0, 200 - len(ws)),
            "catalog_shortfall_to_suggested_200_people": max(0, 200 - len(ps)),
        }
    report = {
        "release_id": atlas.release,
        "snapshot_hash": atlas.snapshot_hash,
        "catalog": atlas.info()["catalog_counts"],
        "scientific_records": atlas.info()["counts"],
        "work_kinds": dict(Counter(w["kind"] for w in works)),
        "work_insight_memberships": atlas.db.execute(
            "SELECT COUNT(*) FROM work_members WHERE snapshot=?", (atlas.release,)
        ).fetchone()[0],
        "work_connections": atlas.db.execute(
            "SELECT COUNT(*) FROM work_links WHERE snapshot=?", (atlas.release,)
        ).fetchone()[0],
        "topic_without_work": [t["id"] for t in topics if not t["work_count"]],
        "subjects": subjects,
        "human_reviewed_contributions": atlas.info()["human_reviewed"],
        "selection_source_families": dict(
            Counter(urlparse(p["bio_sources"][0]["url"]).hostname for p in people)
        ),
        "limitations": [
            "Catalog membership establishes documented relevance, not verified insight-level support.",
            "Most new achievement entries are a source-backed extraction backlog; they do not have completed maps.",
            "Nobel, Fields, Abel and institutional computing selections privilege recognized traditions and omit many important teams, regions and earlier discoveries.",
            "The full ACM Turing Award listing was inaccessible in this source pass. Selected computing figures use other institutional evidence.",
            "Broad award citations remain research-result or research-program entries; they are not invented paper titles. Recognition years are not discovery years.",
            "Exposition works preserve evidence provenance; their authors are not automatically credited with originating every explained insight.",
            "Independent discoveries remain distinct. Shared topics and shared insights do not establish historical influence.",
            "Small spelling corrections and named concept expansions are offline and bounded; arbitrary semantic paraphrases are not guaranteed.",
            "No qualified human audit has been performed. Personal Trace a discovery retains the limitations documented in the 1.3 live evaluation.",
        ],
    }
    assert not report["topic_without_work"], report["topic_without_work"]
    write_json(root / "reports/catalog-1.4.json", report)
    print(
        {
            k: report[k]
            for k in [
                "release_id",
                "catalog",
                "work_insight_memberships",
                "work_connections",
                "human_reviewed_contributions",
            ]
        }
    )
