# Principia-Legacy 1.5 — local review candidate

Updated **28 October 2026**. Reader **1.5.0rc3**, immutable atlas **1.5.0-review4**. Branch `codex/atlas-1.5` starts from merged 1.4.1 (`7732dda`). [Open the local preview](http://127.0.0.1:8767/) · [Current feedback verification](reports/cloud-review4-20261027.md) · [Original 1.5 acceptance](reports/acceptance-1.5.md).

The software and expanded corpus are prepared for local review. **The complete coverage and performance targets are not achieved.** Public deployment remains 1.4.1; no GitHub publication was made.

## Cloud reconnection follow-up · 28 October

The reported overnight failure was an exited SSH child left behind a running
local reader. The private server remained healthy. A single supervisor now
recreates the tunnel after disconnection or a failed health probe, including
startup without connectivity. Pending atlas reads show a reconnection notice and
resume without clearing the current query. The Mac preview now starts at login
and restarts if its local process exits. No corpus, public deployment, credentials
or paid-model retry policy changed. **154 backend checks, 42 final desktop/mobile
checks and two real interruption tests passed**; the interrupted searches recovered
in 4.0 and 4.9 seconds without reloading. [Verification](reports/cloud-reconnect-20261028.md).

## Previous feedback fixes · 27 October

- **Semantic retrieval on the private server:** keyword and spelling search retain priority; an empty result can return explicitly labelled semantic suggestions. The index pins the scientific snapshot and encoder hashes. No provider key or paid model call is needed to browse. The frozen 35-query development benchmark retains hit@10 **0.9697**, with warm server p95 **20.0 ms**. This is not unrestricted language understanding; two broad paraphrase smoke cases still return no result under the conservative similarity threshold.
- **Neuroscience coverage is explicit:** “neuronal state space” now finds one new topic and two publisher-verified papers. These are metadata-only readings, with **zero new screened insights or relationships**. Extraction and an evidenced route remain pending.
- **Simpler topic selection:** an optional searchable area filter displays at most eight choices. Pinned reading views no longer wait for homepage suggestions on reload.
- **Cloud data, small local app:** the private server holds SQLite, canonical data and the semantic model/index. The local preview package is **3.19 MB installed / 1.48 MB zipped**, requiring SSH/network access. Duplicate validation extractions and synthetic stress data were removed; unique scientific evidence, Git history and sealed offline archives remain.
- **Checks:** 152 backend tests and 38 desktop/mobile browser journeys passed; TypeScript, build, lint and 24,588-record validation passed. Measured first view was **3.13 s**, local browser-plus-reader RSS **712 MB**. Thirty requests at concurrency six all succeeded; end-to-end p95 was **557 ms**, including the SSH network path. Initial/intermediate navigation failures and fixes are retained in reports. No paid LLM request was made for this update; human review remains zero.

| Subject | Insights | Topics with content | Route-ready topics | Shortfall: insights / routes |
|---|---:|---:|---:|---:|
| Mathematics | 1,007 | 101 | 12 | 0 / 88 |
| Physics | 1,079 | 105 | 15 | 0 / 85 |
| Computer science | 1,303 | 94 | 13 | 0 / 87 |
| Economics | 968 | 92 | 6 | 32 / 94 |
| Biology & medicine | 1,142 | 93 | 4 | 0 / 96 |

The milestone is **1,000 substantive insights and 100 evidenced routes per subject**. Catalogue size is **1,151 topics, 1,211 works and 904 selected individuals**; **568 works** contain extracted insights. There are **485 topics with content**, **50 route-ready topics**, **4,113 relationships**, **141 joint-premise relationships**, **four cross-subject relationships**, and **855 isolated insights**. Registered entries and graph connectivity do not certify a complete explanation. The longer-term 200-topic/2,000-insight target per subject remains unchanged.

## What changed

- Expanded from **2,905 to 5,499 insights**, and **1,941 to 4,113 relationships**. Fourteen balanced foundation batches, engineering sources and five-topic-per-subject calibration were processed with retained failures. The 406 recovered candidates underwent evidence and editorial review; **44 insights and 10 relationships** entered through that recovery path.
- Withheld **33 overstated cross-work arrows**, thermodynamic and CLT scope errors, **26 non-substantive fragments**, and **15 duplicate extractions** across the DML and final same-source audits. Changed interpretations require fresh approval; old snapshots remain reproducible. Darwin and Wallace remain distinct.
- Added indexed SQL pagination, bounded collection reads, compact snapshot summaries, shared historical search data and browser-worker exploration shards. The final database is **253 MB**. The reader omits unselected internal development indexes; canonical checkpoints remain in the source archive and server.
- Preserved search and reading context, independent topic-list pagination, accessible graph/list alternatives, subject-aware discoveries, global settings and local saved-map metadata. The inspector leads with the intellectual claim.
- Established private authoritative staging with a single admission writer, journal recovery and exact-hash backups. Final public review data were restored on the Mac; private evidence restoration and index rebuilding were tested on Linux. Personal exploration data remain browser-local.

## Previous review3 verification and unresolved work

- **145 backend tests; 317 browser tests passed, three deliberate skips.** TypeScript and focused Python lint checks passed. All **24,588 immutable record versions** passed schema validation; current readable claims and relationships have exact machine-review pins. Five flagship maps, three tour comparisons, 16 dependency-complete briefs and a fresh 100-insight/150-relation human-audit sample are included.
- Frozen retrieval hit@10 is **0.9697**; warm p95 **16.5 ms** on the final corpus. Matched 1.4.1 content preserved relevance while reducing warm p95 from **142.84 to 13.78 ms**.
- Final local browser first view: **512 ms**; measured combined reader/browser RSS: **991 MB**; zero background external requests. At 100,000 synthetic insights, broad-query p95 **2.50 s** and combined memory around **1.28 GB** miss the targets. Distinct searches and neighborhoods remain within their targets at that size.
- **54 live browser attempts across three exact model IDs** are preserved. The last six-query V4.1-Flash run returned all six maps in **142–193 seconds**; four met the structural-route check. GPU/CUDA and ChatGPT remained incomplete. Only one met both timing targets. Source support and scientific validity are not established by passing a structural check.
- **Human review: zero.** The stratified audit is prepared, not performed. Further semantic deduplication, attribution review and broader coverage remain necessary.

Retained review3 offline packaging: approximately **456 MB installed / 104 MB download**; source archive **577 MB installed / 125 MB download**, retaining all internal history. Clean extraction, checksums, source first launch and offline operation passed on macOS. Linux launcher/offline checks passed on the restored dataset; Windows is untested. These archives do not contain review4's new metadata or optional semantic index. [Packaging evidence](reports/package-verification-1.5.json).

## Spending

Known authoring estimates: **CNY232.87**. Uncertain-request reserve: **CNY50.76** across 104 unresolved outcomes. Other reservations total **CNY300.44**, including the separate **CNY300 browser-test hold**. All five browser matrices report **CNY25.94** known token usage, already covered by that hold. Conservative combined exposure is **CNY584.08** against the **CNY1,500** planning ceiling within the additional USD300-equivalent allowance. These are estimates, not the provider bill. No incomplete request is assumed free.

The campaign's last frozen batches contain acquisition failures, provider throttling and attention-guard stops; they were not silently resubmitted. The allowance is not exhausted. [Receipts and inspection](reports/usage-1.5.json).

## Next bounded batch

After local feedback: inspect unresolved provider charges; repair the two failed exploration routes with better primary-source retrieval; finish existing economic explanations before new catalogue growth; improve and independently recheck 25 existing topic routes (five per subject); review semantic duplicates and isolated foundations. Do not add arrows to meet a count. No new paid campaign is running or scheduled by this delivery.

[Installation and local review](docs/LOCAL_PREVIEW.md) · [Release notes](docs/RELEASE-1.5.md) · [Historical 1.4.1 status](reports/build-status-1.4.1.md)
