# 1.5 local acceptance report

**2026-10-26T15:44:28+00:00 · reader 1.5.0rc1 · atlas 1.5.0-review3**
Snapshot SHA-256: `91cc105fd32a448bf7a3e3e0c30d82dfd9701f351f1127cfaab56488bcffcd5d`

This is a locally runnable exploratory candidate. The reader's functional checks pass, while the corpus milestone, consistent live-exploration quality and some 100,000-insight performance targets remain unmet. **It is not a certification that the full 1.5 plan is complete or that the science has received qualified human review.** Public 1.4.1 and GitHub publication remain unchanged pending owner acceptance.

## Software readiness

The upgrade retains a Python-standard-library/SQLite reader and a React/TypeScript interface. Compilation, collection queries, graph queries and exploration indexes are separate focused modules. There is no ORM, second database service or new global frontend state framework. SQL filtering and bounded bulk reads replace repeated full collection scans in normal browsing. Snapshot summaries and internal checkpoint selection avoid repeated large manifest decoding and unnecessary historical indexes.

Topic, work and person collections paginate independently. Existing offset clients and revision-pinned historical links remain supported; new cursor requests bind their release, filters and limits. Graph responses remain capped at 200 nodes, with complete joint premises. Saved map listings use metadata records. Private exploration ranks compressed public shards locally in a worker, without the old 10,000-record ceiling, then hydrates bounded matches.

Navigation now retains the subject, coverage, search, pagination, graph/list state and connection filters. Contextual Back restores the originating view, scroll and keyboard focus; the inspector leads with the claim. Source and profile metadata load on demand. Desktop/narrow-screen journeys, KaTeX, arrows, incomplete-content states and keyboard flows are exercised by browser tests. A direct visual pass also checked fuzzy Turing search, his profile, returning to results, and the final preview.

| Check | Actual evidence |
|---|---|
| Backend | **145 passed**; final duplicate-arrow regression also passed in the 12-test expansion suite |
| Browser | **317 passed, three skipped** against the final snapshot and bundled UI |
| Skips | Desktop-only geometry, catalogue traversal and first-view measurement are not repeated in the mobile project; mobile interaction tests run separately |
| Build | TypeScript type check and Vite production build pass; Vite retains a large-chunk advisory |
| Python lint | Focused E4/E7/E9/F checks pass; not a claim that all legacy style warnings were removed |
| Integrity | **24,588** immutable versions pass JSON Schema validation; IDs, pins, source closure, exact machine verdicts, five endpoints and neighborhood/joint-premise bounds pass |
| Duplicate gate | No repeated same-source, same-credit, same-date exact claim remains. Independent credit and mathematical case are preserved. Semantic equivalence still needs editorial judgment |
| Living behavior | Real five-flagship corrections in a disposable copy invalidate dependent interpretations, remove changed claims from browsing/briefs and preserve older snapshots. Final duplicate correction also invalidated a route badge |
| Research fixtures | Frozen 30 development and 90 held-out files remain hash-identical; older pilot findings are not rerun or promoted into a new positive claim |

The detailed results are in [integrity](integrity-1.5.json), [living checks](living-1.5.json), [coverage](coverage-1.5.json), and [test results](verification-1.5.json). Clean reader/source extraction, checksum verification, actual-key exclusion and network-denied reading passed on macOS. Source first launch rebuilt review3 using the shell launcher. Linux also passed the shell-launcher and offline-reader checks in a disposable tree restored from the verified canonical backup. Windows launch scripts are supplied but were not executed on Windows. [Packaging evidence](package-verification-1.5.json). The installed reader is about 456 MB (104 MB download), below the 500 MB target. The source archive retains all internal history and is about 577 MB installed before rebuilding its index; both remain below 1 GB. Sealed archive hashes are supplied beside the downloads.

## Corpus coverage and scientific limits

| Subject | Insights | Topics with content | Route-ready topics | Shortfall: insights / routes |
|---|---:|---:|---:|---:|
| Mathematics | 1,007 | 101 | 12 | 0 / 88 |
| Physics | 1,079 | 105 | 15 | 0 / 85 |
| Computer science | 1,303 | 94 | 13 | 0 / 87 |
| Economics | 968 | 92 | 6 | 32 / 94 |
| Biology & medicine | 1,142 | 93 | 4 | 0 / 96 |

The target is 1,000 insights and 100 route-ready topics in each subject. The atlas has **1,150 registered topics**, **485 topics with content**, **50 ready routes**, **1,209 works**, **568 works with insights**, **904 selected people**, **5,499 insights** and **4,113 relationships**. Counts use unique primary-subject insights; shared membership does not multiply them. **855 insights remain isolated**. Four warranted cross-subject links are reading prerequisites or a bounded analogy; no new historical influence is implied.

A ready route requires at least eight substantive insights, a resolved endpoint, connected evidenced core, an explicit foundation, limits/gaps and a current pinned machine editorial assessment. Merely registering a topic, extracting eight records or drawing a connected graph does not meet this standard. Work membership means documented relevance or exposition, not priority. Sixty-two pending topics now link to verified publisher reading locations without claiming checked insights.

Recovery retained 44 insights/10 relationships after examining the 406 unpublished candidates. Calibration admitted 135/158; fourteen frozen foundation batches and bounded engineering batches supplied further material. Failed acquisitions and provider attempts remain in [campaign closeout](campaign-closeout-1.5.json). Editorial corrections withheld overstated arrows, scope errors, routine fragments and duplicate extractions while preserving their versions. The additional substance pass checked 2,469 of 2,637 planned candidates; 168 lacked a completed extra editorial verdict. This is distinct from their earlier source-based screening and is an unresolved editorial gap.

Source-based model verdicts are fallible. Institutional/prize selections have geographic and disciplinary biases. Textbook exposition dominates much of the new foundational material, and source completeness, deeper ancestry, semantic deduplication and scientific standing need further specialist review. The pipeline does not infer influence from shared membership or manufacture connections to improve a drawing.

**No qualified human audit or human review was performed.** The [100-insight/150-relation audit sample](human-audit-1.5.json) pins this release and leaves human findings unfilled. Five maps, three tour comparisons and 16 read-only evidence briefs are indexed in [evidence exports](evidence-1.5/index.json). A tour juxtaposes explanations unless an independently warranted cross-subject edge exists.

## Retrieval and performance

A frozen 35-case development set covers topics, works, ideas, people, spelling variants, synonyms, ambiguous names and missing results. It is not a held-out scientific evaluation. On identical 1.4.1 content, hit@10 stayed **0.9394** and MRR **0.9242**, while warm p95 fell **142.84 → 13.78 ms**. Expanded final coverage reaches hit@10 **0.9697**, MRR **0.9545**, warm p95 **16.47 ms**; both missing-result cases are correct. One positive case still misses. [Matched comparison](retrieval-1.5-same-content.json) · [Final results](retrieval-1.5-final.json).

Final fresh local Chrome first view is **512 ms**. Combined RSS is **991.3 MB**, with **zero background external requests** and no page errors. This RSS sum scopes the reader and that browser's process tree; shared pages can be counted more than once. It excludes unrelated test browsers and authoring compilers. HTTP and browser measurements use loopback; remote tunnel/network latency is a separate deployment cost. [Browser measurement](browser-performance-1.5.json) · [HTTP measurement](performance-1.5.json).

Synthetic fixtures are excluded from the scientific corpus. Four concurrent queries were used at each size:

| Synthetic insights | Broad search p95 ms | Distinct search p95 ms | Neighborhood p95 ms |
|---|---:|---:|---:|
| 10,000 | 360.5 | 141.2 | 406.1 |
| 50,000 | 1199.4 | 327.1 | 50.7 |
| 100,000 | 2504.8 | 334.2 | 89.3 |

Broad queries miss the 500 ms target at 50,000 and 100,000 insights. At 100,000, browser-worker warm broad matching is about 113 ms, but combined browser/reader RSS is about 1.28 GB, above the approximate 1 GB goal. Authoring compilation peaked higher and is not reader memory. Two query experiments did not solve the broad-query limit and were not adopted. These results establish a practical limitation, not a claim of unlimited SQLite scalability. [Scale reports](scale-100000-reader-1.5.json) · [Browser scale](browser-scale-1.5.json).

## Live personal exploration

There were **54 real browser attempts** across `deepseek-ai/DeepSeek-V4.1-Flash`, `deepseek-ai/DeepSeek-V4-Flash`, and `deepseek-ai/DeepSeek-V4-Pro`. Model identity is never silently substituted. Earlier timeouts, 429/503 responses, glossary echoes and incomplete graphs are preserved. Fixes addressed route selection, evidence packet crowding, bounded empty-composition recovery and provider coordination.

The final Flash-only matrix ran after this project's bulk authoring stopped, on the explicitly pinned QA2 evidence collection and the archived final exploration bundle. Later changes were atlas editorial corrections, internal-index packaging and singular/plural UI wording; this is not a claim of a new paid run against the review3 corpus. All private raw responses and generated test maps remain on the Mac, outside published archives.

| Query | Finish seconds | First insight seconds | Structural route | Both timing targets |
|---|---:|---:|---|---|
| lithography machines for chip | 178.9 | 63.9 | Pass | Miss |
| Plasma-enhanced chemical vapour decomposition | 141.6 | 62.8 | Pass | Miss |
| resuable rocket | 172.9 | 63.8 | Pass | Miss |
| GPU and cuda | 175.1 | 53.7 | Incomplete | Pass |
| Alphafold | 183.1 | 59.8 | Pass | Miss |
| large language models such as chatgpt | 193.1 | 67.9 | Incomplete | Miss |

All six returned maps, four passed the structural diagnostic, and one met both the 60-second first-insight and 180-second completion targets. GPU/CUDA's hardware and programming branches remained disconnected; ChatGPT retained disconnected foundations and no checked frontier-role endpoint. AlphaFold's refinement also contains potentially repetitive concepts. Structural success does not establish completeness, priority, independent attribution or scientific truth. These failures remain open, and personal exploration stays explicitly experimental. [Final aggregate and primary-assistant assessment](live-browser-1.5-final-flash.json) · [Earlier iteration](live-browser-1.5-iteration4.json).

## Operations, privacy and spending

Canonical data reside under private server staging, separate from deployed code. Acquisition/model calls can run concurrently; admission, corrections and snapshot activation use one writer and an idempotent journal. An interrupted commit is recovered before the next writer proceeds. Backups contain hashes of the exact archived bytes; restoration rejects unsafe paths, inventory changes and hash mismatches. The final public review copy restored **462 files** on this Mac and rebuilt the index in **33.2 seconds**. A full private backup restoration on Linux is recorded separately. SSH interruption and reconnection recovered the same pinned snapshot. [Off-host review](offhost-restoration-final-1.5.json) · [Private restoration](final-review3-restoration-1.5.json) · [SSH test](ssh-reconnection-1.5.json).

Reading is standard-library-only and offline. External network attempts are denied in the offline verification, and browser requests are checked separately. SQL is parameterized; reader routes are read-only; file serving, unsafe URLs/HTML, private-address downloads, size limits, prompt injection and credential exclusion have regression coverage. Personal research queries are not sent to the atlas server; bounded public record IDs can still reveal which public records were fetched. The provider and literature services receive direct research requests under their own policies.

Known authoring estimates: **CNY232.87**. Uncertain-request reserve: **CNY50.76** across 104 unresolved outcomes. Other reservations total **CNY300.44**, including the separate **CNY300 browser-test hold**. All five browser matrices report **CNY25.94** known token usage, already covered by that hold. Conservative combined exposure is **CNY584.08** against the **CNY1,500** planning ceiling within the additional USD300-equivalent allowance. These are estimates, not the provider bill. No incomplete request is assumed free.

Prices and attention-threshold inspection are dated in [usage](usage-1.5.json). Some final frozen jobs stopped at the earlier attention guard and were not silently retried after inspection. The remaining allowance is not claimed as spent. There is no billing dashboard or exact charge enforcement.

## Acceptance boundary

Accepting this candidate would mean accepting a larger exploratory collection and a tested local reader, with the documented gaps. It would not certify completion of 500 routes, robust scientific outputs for every model/query, 100,000-insight broad-search performance, or expert scientific review. The next bounded work should strengthen existing routes and primary-source retrieval before adding catalogue entries.

The public deployment was independently observed at **1.4.1-exploratory**. The original dirty development folder and older releases remain preserved. Local Git records the upgrade on `codex/atlas-1.5`; public deployment and GitHub publication await subsequent authorization.
