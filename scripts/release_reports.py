"""Create transparent coverage, usage, audit and evidence reports from actual records."""

from collections import Counter, defaultdict
from pathlib import Path
import random
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from principia_legacy.common import read_json, write_json, write_lines
from principia_legacy.storage import Atlas
from principia_legacy.records import visible
from principia_legacy.release import report

root = Path(__file__).resolve().parents[1]
atlas = Atlas(root)
records = atlas.records
summary = report(root)
catalog = read_json(root / "reports/catalog-1.4.json", {})
write_json(root / "build/source-attempts.json", summary["source_attempts"])
write_json(
    root / "build/coverage.json",
    {
        "release_id": atlas.release,
        "counts": summary["counts"],
        "coverage": summary["coverage"],
        "targets": summary["target"],
        "target_met": summary["content_target_met"],
        "shortfall_by_subject": summary["shortfall_by_subject"],
        "dossiers": atlas.dossiers()["dossiers"],
    },
)
from principia_legacy.common import read_lines

receipts = list(
    {
        r["trace_id"]: r
        for r in [
            *read_lines(root / "reports/usage-receipts.jsonl"),
            *(read_json(p) for p in sorted((root / ".work/receipts").glob("*.json"))),
        ]
    }.values()
)
write_lines(root / "build/usage-receipts.jsonl", receipts)


def stratified(items, count, key):
    groups = defaultdict(list)
    for item in sorted(items, key=lambda r: r["id"]):
        groups[key(item)].append(item)
    rng = random.Random(894103)
    for group in groups.values():
        rng.shuffle(group)
    chosen = []
    while len(chosen) < count and any(groups.values()):
        for group in sorted(groups):
            if groups[group] and len(chosen) < count:
                chosen.append(groups[group].pop())
    return chosen


nodes = [r for r in records if r["type"] == "contribution" and visible(r)]
edges = [r for r in records if r["type"] == "relation" and visible(r)]
by_id = {r["id"]: r for r in nodes}
node_sample = stratified(nodes, 100, lambda r: r["pillar"])
edge_sample = stratified(
    edges,
    150,
    lambda r: (by_id[r["conclusion"]["id"]]["pillar"], r["layer"], r["predicate"]),
)
sample = {
    "release_id": atlas.release,
    "status": "prepared; no qualified human audit performed",
    "selection": "Fixed seed 894103; equal pillar cycling for contributions; pillar/layer/predicate cycling for relations; without replacement",
    "requested": {"contributions": 100, "relations": 150},
    "actual": {"contributions": len(node_sample), "relations": len(edge_sample)},
    "strata": {
        "contributions_by_pillar": dict(Counter(r["pillar"] for r in node_sample)),
        "relations_by_predicate": dict(Counter(r["predicate"] for r in edge_sample)),
    },
    "items": [
        {
            "id": r["id"],
            "revision": r["revision"],
            "content_hash": r["content_hash"],
            "type": r["type"],
            "source_anchors": r["anchors"],
            "reviewer": None,
            "judgment": None,
            "rationale": None,
            "completed_at": None,
        }
        for r in [*node_sample, *edge_sample]
    ],
}
write_json(root / "build/audit-sample.json", sample)
for dossier in ["M06", "P01", "C01", "E01", "B01"]:
    write_json(
        root / "docs/evidence" / (dossier + ".json"),
        atlas.brief("Flagship evidence: " + dossier, dossier=dossier),
    )
    write_json(
        root / "docs/maps" / (dossier + ".json"),
        atlas.neighborhood(dossier=dossier, limit=200),
    )
normative = [r for r in nodes if r["kind"] == "normative_argument"]
write_json(
    root / "docs/normative-collection.json",
    {
        "release_id": atlas.release,
        "notice": "Attributed arguments, not empirical findings or a consensus policy. No normative source grants authority.",
        "contributions": [atlas.inspect(r["id"], "contribution") for r in normative],
    },
)
lines = [
    "# Current coverage",
    "",
    "Counts describe admitted, visible records. Empty assignments and rejected sources remain visible gaps. A source catalog is a plan, not completed coverage. Shared insights appear in multiple topics but count once in the corpus.",
    "",
    "| Topic | Contributions | Relations | Status |",
    "|---|---:|---:|---|",
]
for d in atlas.dossiers()["dossiers"]:
    lines.append(
        f"| {d['id']} — {d['title']} | {d['contribution_count']} | {d['relation_count']} | {d['status'].replace('_', ' ')} |"
    )
(root / "docs/COVERAGE.md").write_text("\n".join(lines) + "\n")
print(
    {
        "counts": summary["counts"],
        "audit": sample["actual"],
        "normative_arguments": len(normative),
        "usage": summary["usage"],
    }
)
atlas.close()

status = (
    "Local exploratory candidate; not deployed or published"
    if "--final" in sys.argv
    else "Implementation and bounded source passes remain active"
)
counts = summary["counts"]
usage = summary["usage"]
topic_count = len(summary["gaps"])
populated = sum(c["populated_topics"] for c in summary["coverage"].values())
coverage_rows = "\n".join(
    f"| {p.replace('_', ' ')} | {c['populated_topics']} | {c['contributions']} | {summary['shortfall_by_subject'].get(p, {}).get('populated_topics', 'n/a')} / {summary['shortfall_by_subject'].get(p, {}).get('unique_primary_subject_insights', 'n/a')} |"
    for p, c in summary["coverage"].items()
)
target_status = (
    "Numeric coverage targets met; depth and evidence gaps still apply"
    if summary["content_target_met"]
    else "Not met"
)
attempts = Counter(x["state"] for x in summary["source_attempts"])
body = f"""# Build status

{status}. This file reports actual admitted content, not the founding project's ambitions.

| Dimension | Current evidence |
|---|---|
| Corpus | {counts["contribution"]} contributions, {counts["relation"]} relationships, {counts["source"]} source records |
| Work catalogue | {catalog.get("catalog", {}).get("works", "n/a")} works; {catalog.get("catalog", {}).get("people", "n/a")} selected people; {catalog.get("catalog", {}).get("works_with_insights", "n/a")} works with extracted insights. Metadata-only entries do not increase scientific coverage. |
| Scope | Five subjects; {topic_count} registered topics, {populated} populated; empty assignments remain visible |
| Expanded content target | **{target_status}**: at least 200 populated topics and 2,000 unique primary-subject insights per subject. Counts never override the evidence requirement. |
| Machine screening | Passage-grounded extraction and a separate critic; exact-revision provenance retained |
| Human review | **{summary["human_reviewed_contributions"]} contributions with recorded human review; qualified human audit {summary["independent_human_audit"]}** |
| Audit preparation | {len(node_sample)} contributions and {len(edge_sample)} relationships sampled; adjudication fields empty |
| Research pilot | 120 frozen synthetic cases, 30 development / 90 held out; five conditions, 600 recorded case attempts |
| Normative content | Attributed normative arguments remain distinct from empirical findings |

| Subject | Populated topics | Unique insights | Remaining topics / insights |
|---|---:|---:|---:|
{coverage_rows}

The original release's 3,000-relationship lower target is also still a planning reference: the current shortfall is {max(0, 3000 - counts["relation"])}. Relationships are admitted only when separately warranted.

The typed-atlas condition did not improve rule-based verdict agreement over flat cards in the synthetic pilot. Boundary removal performed worse. One untyped-graph response was missing and remains counted. These measurements do not establish semantic correctness or stronger alignment. Exact input token equality was not achieved; the pilot used common context character ceilings and recorded actual token receipts.

## Source and usage receipts

- Source-pass outcomes: {dict(attempts)}. Failures, abstentions and rejected bridges remain in reports or quarantined authoring records.
- Provider attempts: {usage["requests"]}; successful: {usage["successful"]}; unknown possible charges after interruption/timeout: {usage["unknown_possible_charge"]}.
- Separate interruption markers: {usage["interruption_markers"]}; up to {usage["unreceipted_interruption_upper_bound"]} additional in-flight requests may lack individual receipts. These are not counted as free.
- Reported usage: {usage["prompt_tokens"]:,} prompt tokens; {usage["completion_tokens"]:,} completion tokens. These totals exclude unreported usage for interrupted requests.
- Unpriced model requests: {usage["planning_estimate"]["unpriced_requests"]}. The dated-rate known subtotal excludes these and all unreported usage; it is not the complete cost. Personal browser-test receipts are reported separately in the current acceptance report.
- US$300-equivalent planning allowance is owner-managed. No exact bill or hard spending enforcement is claimed.
- Model identities appear in individual receipts. Flash handled the expansion and its separate relationship critic; Pro was used for calibration, editorial triage and the stricter cross-source warrant check. No silent model substitution.

## Verification and remaining limits

Software checks cover schemas, references, source anchors, joint premises, four-category bounded fuzzy/concept search, work membership, read-only serving, correction quarantine and recheck, stale approvals, preserved snapshots, unsafe inputs and export closure. Browser tests cover desktop and narrow-screen reading, sources, arrows, search, comparison, keyboard access, filtering, expansion and brief content. The offline smoke test denies outbound socket connections while serving and reading all bundled assets; browser routes separately block external requests.

Measured results are in `build/performance.json`, and the research results in `build/evaluation-summary.json`. Only macOS was actually tested here. Windows and Linux launchers plus a three-platform CI workflow are supplied; those platforms have not been executed in this session.

The current content is a bounded set of explicit source passes. It is not a completed recursive depth-six reconstruction of the history of science. Independent priority, inaccessible sources, exact current frontier relevance, unresolved endpoints and alternative traditions need further source work. Three tours are reading sequences; they do not invent cross-pillar historical arrows.

Representative-selection counts and per-subject shortfalls are in `reports/catalog-1.4.json`. Personal Trace a discovery remains experimental under the unchanged live-evaluation limitations in `reports/product-readiness-1.3.md`. This catalogue upgrade does not certify unattended public research.

Next bounded content work: resolve the gaps enumerated in `docs/COVERAGE.md` and `build/coverage.json`, admit precise endpoints, then extend each neighborhood from its explanatory checklist. Keep count targets subordinate to evidence. A prepared human-audit queue is available in `build/audit-sample.json`.
"""
(root / "BUILD_STATUS.md").write_text(body)

if "--final" in sys.argv:
    import shutil

    public = root / "reports"
    public.mkdir(exist_ok=True)
    for name in [
        "coverage.json",
        "source-attempts.json",
        "editorial-screening.json",
        "editorial-correction.json",
        "calibration.json",
        "calibration-identity-repair.json",
        "audit-sample.json",
        "evaluation-summary.json",
        "evaluation-results.jsonl",
        "calibration-summary.json",
        "bridge-screening.json",
        "usage-receipts.jsonl",
        "performance.json",
        "browser-performance.json",
        "offline-verification.json",
        "living-verification.json",
        "test-report.txt",
        "acceptance.json",
    ]:
        if (root / "build" / name).exists():
            shutil.copy2(root / "build" / name, public / name)
