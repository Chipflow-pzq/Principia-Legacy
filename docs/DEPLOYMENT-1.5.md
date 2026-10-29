# Public deployment · 1.5.0

The owner accepted review5 on 29 October 2026 and authorized production deployment plus a GitHub PR, with manual merging reserved to the owner.

## Scientific and software provenance

- Accepted development code: `aecc810`, preserved on `codex/atlas-1.5` with its full unpublished corpus and evidence.
- Accepted source snapshot: `1.5.0-review5`, hash `bd2161f6c40e05a9ac52a6aa831de5ab39024aa6f0f642d8d47c06a5f4558dd6`.
- Public snapshot: `1.5.0-exploratory`, hash `dc046696082d63a5b1203255c87ef8c5423c495adfd12ced65f2b320bd71720d`. Only the release identity changes.
- Publication branch: `codex/release-1.5`, based on GitHub main `7732dda`. It carries net software changes without importing the large unpublished data history.

The full cloud atlas contains 5,700 insights, 4,211 relationships and 605 source records. All seven formerly public manifests are identical to those in the old production database. Internal review, working and evaluation snapshots are excluded from the public index and route allowlist. Qualified human auditing remains zero.

## Code, data and recovery

Production uses a versioned code checkout selected by `current`, a separate read-only public data home and an isolated versioned Python runtime. The public SQLite index is 259,166,208 bytes; it is rebuilt using the 1.5 compiler rather than modifying the old schema in place. Semantic vectors and their offline encoder are pinned and checked against this public snapshot.

Canonical JSONL, source evidence, authoring jobs and usage receipts remain in private staging. The GitHub PR retains the previous 1.4.1 reference corpus so a source checkout remains runnable offline; it does not contain the expanded cloud database or model.

The verified private review5 backup has 8,127 files and SHA-256 `a469b5c17979b7bd893c79229983a05ac3372c2519fbdd3ac869b30e472e555d`. Its hash was rechecked before deployment. The old production bundle, runtime, service unit and previous symlink target are retained. To roll back, atomically restore that symlink, restore the saved service unit, reload systemd and restart only the atlas service; the old database and assets remain intact.

## Verification

The publication branch passed 167 backend tests, TypeScript checking and both local and `/web/legacy/` frontend builds. **Activated at 03:59:46 UTC on 29 October 2026**, from code `6cc73ca9319c02d95df0fba388c07f0b7ba548c0`. New service readiness took 2.319 seconds. The existing Nginx configuration was preserved; earlier hashed asset chunks remain available for already-open tabs.

The private canary passed **58 API and boundary checks**. The actual public HTTPS mount passed asset hashes, CSP, private-file denial and health checks. **All six desktop/mobile browser journeys passed**: search, profiles, works, insights, graphs, contextual return, formulas, semantic retrieval, old snapshot links and the exploration/settings interface. The neighbouring demo health check also passed.

One fresh-browser first view took **4.89 seconds**; six network-inclusive searches took **66–330 ms**. Four-client distinct search p95 on server loopback was **44.17 ms**. The two-worker production service used approximately **388 MB** in the sampled measurement, with no service restarts. These are deployment samples, not a broad load guarantee.

[Machine-readable deployment receipt](../reports/deployment-1.5-20261029.json) preserves hashes, exact checks, timing scope and initial diagnostics. Browser tests used Chromium mobile emulation, not physical phones. No paid model generation was rerun for this deployment. This is an operational release of the accepted content; it does not claim new coverage or expert review.

[Accepted coverage audit](../reports/coverage-review5-20261028.md) · [Hosting instructions](../hosting/README.md) · [Historical 1.4.1 deployment](DEPLOYMENT-1.4.1.md).
