# Changelog

## 1.4.1 — 17 October 2026

Promotes the accepted reader to a public release with the unchanged 1.4.1-exploratory scientific snapshot. Updates the project introduction, publishing guidance and hosting documentation. Production activation uses a versioned Git checkout, verified assets and retained rollback configuration.

## 1.4.0-rc.1 / 1.4.1-exploratory — local, 17 October 2026

- Add versioned works between topics and insights, with exact evidence-pinned memberships, individual contributors and scoped connections.
- Search four result types with bounded offline spelling recovery, accents, aliases and curated related concepts; preserve search context through work/profile navigation.
- Match discovery suggestions to the selected subject. Mark source-only topics and pending extraction explicitly.
- Replace automatically generated author-list profiles with a selected, sourced individual catalogue. Add Turing, von Neumann and earlier historical foundations.
- Catalogue 882 works and 899 individuals. Retain 2,905 admitted insights and 1,941 relationships; 262 works have extracted insights, while 620 remain a documented backlog.
- Correct a reversed reduction phrase in the final Turing reading pass and independently recheck both dependent arrows; the earlier 1.4.0 freeze remains reproducible.
- Bound the reader cache to two decoded snapshots without retaining large JSON cache keys.
- Preserve older snapshots, record catalogue differences, and invalidate stale work interpretations after corrections. No qualified human audit or deployment is claimed.


Reader **1.3.1-rc.2**, frozen atlas **1.3.1-exploratory**, awaiting local acceptance. No deployment or push.

Ordinary navigation and old preview bookmarks now open the same exploration workspace. Settings distinguishes software from scientific snapshots. Search prioritizes a named idea over incidental mentions. Snapshot decoding and topic summaries reduce repeated work. Topics disclose isolated insights.

The corpus adds 30 foundation topics and 213 net insights. The complete old relationship collection was checked against pinned passages: 463 arrows were withheld and 23 repaired. Direct corrections address scope, attribution, reduction direction, monodromy, mathematics and evidence locators. Changed records invalidate dependent interpretations; 25 dependent arrows passed fresh checks. A later CLT exposition correction also received new dependent checks. Previous scientific releases, including the interim 1.3.0 snapshot, remain reproducible.

Personal exploration uses browser-owned credentials, bounded generation and evidence checks, inspectable progress, and optional local saving. Refinement now targets the missing entrance to the requested result’s explanatory branch. Actual live outcomes, unsuccessful attempts and limits are in [the acceptance report](reports/product-readiness-1.3.md).

# GitHub source edition — 2026-10-15

Organized the complete source around the deployed 1.2.0-exploratory snapshot. Added a concise README, linked development/contribution/hosting guides, publication hygiene and the deployed read-only hosting adapter. Hosted asset and API prefixes now build from Vite configuration; the public build labels its online, read-only mode. The release CLI requires an explicit immutable identifier.

The canonical corpus, scientific snapshot and historical release hashes are unchanged. Unreleased local curation work remains separate. Verification and input provenance are recorded in `reports/github-source-verification.json` and `docs/provenance/`.

# 1.2.0-exploratory — 2026-10-13

Search now covers ideas, topics and scientists. Reading an idea preserves the results and reading position; its inspector links directly to all containing topics. Scientist profiles include sourced descriptions, credit notes and related ideas/topics. Browser history, reload and early navigation during loading are tested on desktop and mobile.

The corpus grows to **2,667 insights, 2,233 relationships and 237 sources**, across **152 populated topics** (154 registered). Hamiltonian mechanics, general relativity and other classical foundations are included. Twenty-nine researched profiles sit within 679 searchable attribution/person/team pages. Explicit corrections withhold 23 low-value or problematic contributions and quarantine 22 dependent relationships; historical source scope and shared-navigation validity are separately checked.

Validation: 65 backend passes; 46 full-suite browser passes, two intentional skips and two focused startup passes; 10,648 immutable versions validated; 5,404 formulas parsed without errors. The expanded per-subject coverage target is **not met**, and qualified human review remains **zero**. Details, measured performance, usage, research limitations and continuing work are in [the 1.2 release report](docs/RELEASE-1.2.md).

# 1.1.0-exploratory — 2026-10-13

The atlas now contains **1,821 contributions, 1,623 warranted relationships and 145 sources**, with material in all 60 topics. This is an exploratory release with no qualified human audit; it remains 1,377 relationships below the lower coverage target.

The reader now typesets mathematical notation, keeps subject navigation visible while scrolling, uses clearer “subjects/topics” language, and explains the five flagship entry points. Comparison has built-in search; saved links, browser history, keyboard focus, mobile layouts, stable graph expansion and main-result navigation have been improved.

Source expansion is resumable and append-only. Stricter warrant review rejected 36 proposed cross-source edges; ten contribution accounts and dependent interpretations were held through an explicit immutable correction. All prior snapshots and unfavorable research outcomes are preserved. Legacy helpers that rewrote records are retired.

Validation: 55 backend tests; 36 full-suite browser passes and two intentional skips; five focused browser passes after final loading polish; 7,368 immutable versions validated; 2,472 formulas parsed; all five flagship correction checks passed. Offline and clean-package verification, performance, usage, gaps and platform limitations are documented in [the release report](docs/RELEASE_REPORT.md).

# 1.0.0-exploratory — 2026-10-12

First locally runnable exploratory release of Principia-Legacy. The reader contains **817 contributions, 747 warranted relationships and 64 source records**, organized through five pillars and 60 dossier scopes. It includes five flagship maps, three cross-disciplinary reading tours and 32 attributed normative arguments. The corpus is machine-screened; **no qualified human audit has been performed**.

The bundled browser interface supports graph/list navigation, typed arrow inspection, source anchors, search, contextual tracing, comparison, limitations, keyboard access and historical snapshots. Everything required for reading is local. Python 3.12+ is the only reader prerequisite.

Canonical JSONL, immutable versions, SQLite FTS5/adjacency indexes, explicit correction patches, source refresh comparisons, exact-source machine rechecks and dependency-complete selected evidence briefs are included. Seven editorial exclusions were applied as actual revisions, invalidating dependent interpretations while preserving the earlier snapshot. Source records remain distinct from scientific standing and human review.

## Verification

The release was exercised on macOS with Python 3.12.7 and Chrome. Backend and browser results, full exported-schema validation, flagship correction checks, source/version closure, offline socket-denial checks, performance measurements and the prepared 100-contribution/150-relation audit queue are in `reports/`. Windows and Linux launchers and CI jobs are provided; neither platform was run in this session. Narrow-screen checks use browser emulation, not a physical phone.

## Content and research limitations

The targets of 1,500–2,500 contributions and 3,000–5,000 relationships are **not met**. All 60 scopes are visible, but evidence gaps, unresolved endpoints and incomplete ancestry remain. The authoring pipeline performs explicitly configured source passes; this release does not implement autonomous depth-six historical reconstruction or selective pillar archives.

The 120-case synthetic research pilot retains all 600 condition/case attempts, including one missing response. Typed retrieval did not outperform flat cards on rule-based verdict agreement. Context character ceilings and output-token ceilings were shared; input token counts were not exactly matched. The evaluation lacks independent expert gold labels and does not establish improved alignment. Original calibration had 59 exact matching response IDs; its remaining relation was rechecked separately during final verification. These limitations and unfavorable results are preserved, not removed from the release.

Provider receipts are token/attempt records, not a billing statement. The US$300-equivalent allowance remains manually managed; interrupted requests can incur charges even when usage is missing.

## Distribution

The offline archive contains the complete source, canonical corpus, prebuilt assets, compiled database, reports and checksums. The separate source archive omits the rebuildable database. Run `python3 start.py` after extraction. No remote repository or GitHub release was created or published.

Code: MIT. Original project explanations: CC BY 4.0. Third-party source rights remain separate.
