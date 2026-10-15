# Verification evidence

These are measured outputs from the exploratory 1.0 build, not targets or claimed human judgments.

- `acceptance.json`: integrity, exact machine-review coverage, source closure, frozen evaluation files, all 60 scopes and five endpoints.
- `test-report.txt`: backend, browser and offline checks, with their actual execution scope.
- `performance.json`: timings and memory on the test machine; browser page-request accounting.
- `coverage.json`, `source-attempts.json`: admitted counts, unresolved scopes, failures and source-pass outcomes.
- `living-verification.json`: disposable corrections to all five real flagship maps, including preserved snapshots and dependent rechecks.
- `editorial-screening.json`, `editorial-correction.json`: Pro editorial triage, exact-ID repairs, exclusions and explicitly retained background contributions.
- `calibration.json`, `calibration-summary.json`, `calibration-identity-repair.json`: original 20/40 calibration and the separate late check of one misidentified response.
- `evaluation-results.jsonl`, `evaluation-summary.json`: all 600 recorded pilot attempts, actual responses and unfavorable results. Synthetic labels and character-based input ceilings limit interpretation.
- `audit-sample.json`: 100 contributions and 150 relations awaiting qualified human adjudication. Blank fields are intentional.
- `usage-receipts.jsonl`: model identities, hashes, reported tokens, attempt outcomes and unknown possible charges. No API credentials or full downloaded source passages.

The original calibration and evaluation snapshots remain reproducible. A machine review or passing test does not establish scientific correctness or human approval. The source cache is private and absent from distribution; claim-level rechecking requires access to the exact source version.
