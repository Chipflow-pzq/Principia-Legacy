# Completion, quality and search audit

**28–29 October 2026 · reader 1.5.0rc4 · scientific snapshot 1.5.0-review5**

The atlas is not complete. The reported message meant that a real work had been registered, but its passages had not yet been turned into checked explanations. Catalogue coverage had been easier to mistake for explanatory coverage than it should have been. This update repairs that example, expands existing explanations across all five subjects, and makes the remaining gaps inspectable.

**Try the private cloud preview:** [neuronal group communication](http://127.0.0.1:8767/#q=neuronal+group+communication). The authoritative data stay on the server; the Mac runs a roughly 3.2 MB reader. Public production remains on 1.4.1.

## What is actually available

| Measure | Before: review4 | Now: review5 |
|---|---:|---:|
| Admitted insights | 5,499 | **5,700** |
| Admitted relationships | 4,113 | **4,211** |
| Topics with at least one insight | 485 / 1,151 | **509 / 1,154** |
| Works with extracted insights | 568 / 1,211 | **593 / 1,233** |
| Individual profiles with linked insights | 103 / 904 | **113 / 911** |
| Topics meeting the strict reading-route criteria | 50 | **49** |
| Isolated insights | 855 | **926** |
| Admitted cross-subject relationships | 4 | **4** |
| Qualified human reviews | 0 | **0** |

The stricter route count fell after corrections invalidated a previously accepted interpretation. New source-grounded insights can remain isolated until a separately warranted connection is established. Neither increase in catalogue size nor a more connected picture is an admission criterion.

| Subject | Insights | Topics with insights / listed | Works with insights / listed | Profiles with insights / selected | Ready routes / target |
|---|---:|---:|---:|---:|---:|
| Mathematics | 1,035 | 107 / 197 | 124 / 230 | 15 / 113 | 12 / 100 |
| Physics | 1,117 | 110 / 288 | 128 / 308 | 25 / 273 | 15 / 100 |
| Computer science | 1,342 | 98 / 214 | 117 / 230 | 29 / 130 | 12 / 100 |
| Economics | 1,011 | 97 / 180 | 112 / 188 | 24 / 111 | 6 / 100 |
| Biology & medicine | 1,195 | 97 / 275 | 112 / 280 | 30 / 296 | 4 / 100 |

Every subject now exceeds the 1,000-insight numerical milestone. Only **318 topics contain eight or more insights**, and only **49** meet all reading-route requirements. The 100-route-per-subject milestone therefore has **451 routes outstanding**. Works and people can span subjects, so those table columns are not additive. A sourced profile establishes identity and selected credit; it is not a complete biography.

**Outstanding depth:** 640 works have no extracted insights, 645 topics have no admitted insights, and 798 selected individuals have no linked insights. The longer-term 200-topic/2,000-insight goal per subject remains outstanding. [Machine-readable inventory and integrity audit](coverage-summary-review5-20261028.json).

## Repair of the reported neuroscience gap

Three inspectable full-text sources now support the two neuroscience topics:

- Cunningham and Yu, *Dimensionality reduction for large-scale neural recordings* (2014): 14 insights. [Full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC4433019/).
- Churchland and colleagues, *Neural population dynamics during reaching* (2012): 10 insights. [Full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC3393826/).
- Semedo and colleagues, *Cortical areas interact through a communication subspace* (2019): 10 insights. [Full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC6449210/).

The exact query **neuronal group communication** returns the Semedo work, ten extracted insights, five individual contributors, and the communication topic. The topic contains eleven insights and eight relationships: ten from the paper and one shared dimensionality-reduction foundation. The state-space topic contains 24 insights. Original work identities were preserved when passage-grounded material was attached.

The explanation distinguishes predictive relationships and shared variability from causal transmission. Population, species, task and measurement boundaries remain explicit. Three initially accepted formulations were narrowed after primary inspection, then independently rechecked. Two cross-paper teaching links were authored and checked; neither is represented as historical influence. Missing ancestry and two currently unconnected ideas remain visible in the communication topic.

Seven profiles were added as individual people, with source-bound authorship. A selected-author subset is identified as such and never asserted to be the complete author list.

## Expansion and correction work

A balanced 25-assignment campaign and three bounded follow-ups produced **202 accepted candidate insights before deduplication; 201 were retained**. The work addressed existing explanations and foundations, including Euclid, backpropagation, program verification, neural populations, NFS and economic mechanisms. Admission and compilation were separated so incomplete batches could not replace the active reader database.

Routine extraction used the configured Flash model; the exact model identities, inputs, prompt hashes, usage and outcomes remain in the server receipts. A separate DeepSeek V4 Pro check assessed all new candidates and a stratified sample of 100 earlier insights and 150 earlier relations. These were **machine checks**.

- The older relation sample flagged 15 cases: 14 were withheld and one was corrected to a teaching prerequisite.
- Two newly proposed relations and one additional simulation-to-observation link were withheld.
- A duplicate restatement of the Euclid argument and its dependent arrow were withheld; independent intellectual discoveries remain separate.
- Failed acquisition, insufficient evidence, all-withheld outputs and the first malformed-target attempt were preserved. Two automated cross-source connection attempts admitted no arrows; connectivity was not used to override their failures.
- A revision recheck had applied deductive-premise requirements to a teaching relation. The shared predicate contract is now supplied explicitly; the original rejection and the single corrected recheck remain recorded.

All **25,533 immutable record versions** passed validation. Every current visible claim and relation has its exact machine-review pin, an inspectable source revision, evidence anchors and stated limits. Private passage hashes resolved without error. This establishes traceability, not a certificate of scientific truth. Exact duplicate detection preserves the independent Darwin/Wallace pair and does not substitute for semantic or expert review. [Integrity checks](integrity-review5-20261028.json).

A fresh, revision-pinned **100-insight/150-relation human-audit sample** is [prepared](human-audit-review5-20261028.json). It has not been performed. The earlier 120-case research suite was not rerun for this feedback repair; its existing results and limitations are unchanged.

## Search and reader behaviour

The reader now exposes a compact per-subject coverage table. Search cards disclose reading-list-only matches before opening; empty work/topic pages explain what can be read and where to continue. Results lead with topics, works and insights before contributor profiles. On narrow screens, an inspector can return directly to the originating search. Old links retain their pinned data and offer a working route to the current snapshot without discarding the query.

Retrieval preserves keyword and spelling matching, adds vocabulary-checked singular variants, prefers contiguous method names, and handles an explicit example clause. A phrase match no longer suppresses broader catalogue navigation. The regression **difference in differences → generic differences** now yields actual difference-in-differences material. Server-only semantic fallback uses the pinned local encoder; it does not call a provider or upload browsing queries to an inference service. Matched works and topics expose bounded checked memberships; membership is not an influence claim.

The frozen 52-query availability set improved from **37 to 49 queries with content-bearing results**. One remains catalogue-only and two have no result. All four negative controls remain empty. This is a development availability check, **not 94% scientific accuracy or arbitrary-query recall**. The final 35-case retrieval benchmark retained **hit@10 0.9697 and MRR@10 0.9545**. Initial phrase-filter regressions were retained and repaired before acceptance. [Availability before](search-coverage-before-20261028.json), [after](search-coverage-acceptance-20261028.json), [retrieval benchmark](retrieval-review5-acceptance-20261028.json).

Known limitations include broad-query ranking, related-but-secondary results, incomplete biographies and two missed paraphrases: **random variables become normally distributed** and **why light bends near a massive star**. **Emmy Noether** remains a sourced catalogue/profile result without extracted insights. “Nearly any query” is not a supported claim for this finite corpus.

Currency is no longer accidentally consumed as inline mathematics. **15,627 mathematical spans render without KaTeX errors**; this is a rendering check, not a mathematical-proof check. Small maps initially fit their full graph instead of clipping foundational nodes. Larger graphs retain their bounded neighbourhood and explicit overview control. [Formula report](math-review5-20261028.json).

Compact maps use stable grid positions and larger labels, with curved arrows where a straight line would pass through a third node. This avoids a force layout shrinking eleven ideas into unreadable labels. Positions do not imply an unrecorded relationship. [Visually inspected neural topic](screenshots/neural-communication-review5-final.png).

## Software verification and measured limits

- **163 backend tests passed**, followed by 50 focused storage/transport checks after final formatting. TypeScript checking, the production build and targeted lint passed. The build still reports the large bundled vendor/application chunk; measured first view remains below five seconds.
- **92 desktop/mobile browser workflows passed**, with zero retries, failures or skips in the final broad run. After the compact-graph adjustment, **12 affected workflows passed again**. These are overlapping runs, not 104 unique cases. They cover search, sourced work/profile navigation, returning to results, filters, revision links, comparisons, formulas, evidence export, keyboard focus and paginated topic lists. The exhaustive browser traversal was not rerun; all 1,154 neighbourhoods were checked separately by the backend integrity suite. [Broad run](browser-workflows-acceptance-review5-20261028.json), [final graph checks](browser-graph-final-review5-20261028.json).
- Earlier failing browser reports remain in `reports/`. A subsequent bulk-catalogue setup request also timed out; the final test setup now uses the same bounded summary pages as the reader. Legacy unpaginated API exports remain compatible but can be slow over this SSH connection.
- **Two actual interruption tests passed:** terminating the owned SSH process recovered in **4.464 seconds**, and terminating the owned local reader recovered in **4.451 seconds**. Both preserved the query and resumed in the same browser page without reload. They exercise the installed Mac login service, not public infrastructure. [SSH recovery](cloud-live-ssh-review5-20261028.json), [reader recovery](cloud-live-reader-review5-20261028.json).
- Fresh desktop first view was **2.703 seconds**. The measured local browser-plus-proxy RSS was **732,073,984 bytes**, with approximately 16.1 MB JS heap, no page errors and zero external browser requests. The remote service was measured separately at approximately 279 MB current / 320 MB peak. Blocking browser external requests does **not** make this SSH-backed preview offline. [Browser measurements](browser-performance-review5-accepted-20261028.json).
- Warm server search p95 was **60.03 ms** on the 52-query availability set. Twenty-one loopback neighbourhood reads had **9.63 ms p95**, maximum 25.87 ms. Over the Mac-to-cloud SSH path, 20 sequential searches had **1.159 seconds p95**; 24 distinct searches at concurrency four had **2.150 seconds p95**. Seven neighbourhood reads had **1.298 seconds median and 5.506 seconds maximum/p95**. All 59 health/search/graph reads completed, but the network-inclusive 500 ms / one-second targets are **not met consistently**. [Cloud-link measurements](cloud-latency-review5-20261028.json), [server neighbourhood measurements](server-neighborhood-latency-review5-20261028.json).
- Release comparisons now fetch 20 records per category and cancel obsolete requests. The first page fell from **1,719,272 to 33,867 compressed bytes**, a 98% reduction; the sampled first/second pages took 2.94/1.75 seconds over SSH. Source/review totals and exact historical revision links remain available. [Comparison measurements](changes-pagination-review5-20261028.json).

The installed thin reader contains **3,207,277 bytes**, with 81 file checksums verified. The **1,487,123-byte ZIP** was reopened and every member verified against those checksums. It contains no canonical database, encoder, authoring credentials or source cache; the configured SSH host and network are required. Mac startup, Linux private serving and Linux backup restoration were tested. Windows was not tested in this repair. The retained review3 offline package is older and does not contain review5. [Package receipt](packaging-review5-20261028.json).

**Software assessment:** the tested local review workflows are ready for inspection. **Corpus assessment:** the route target, broad explanatory depth, expert review and consistent network-inclusive latency remain unfinished. The current evidence does not justify a claim that nearly any scientific query has a complete answer.

## Operations and spending

Canonical files, evidence, jobs and receipts remain authoritative under the private server staging data home. The rebuildable reader database is **297,844,736 bytes**. The private service stays loopback-only, with SSH access from the Mac. No cloud corpus or encoder was copied into the installed local preview. User exploration keys and saved maps were not touched.

A compiler permission defect was repaired: an atomically replaced reader index now remains readable by its separate service account. Under extended browser tests, tunnel health handling was also tightened: an individual failed request no longer marks every channel disconnected, and successful concurrent responses prevent an inappropriate tunnel restart. Actual lost connections still trigger automatic recovery. Diagnostics record exception types, never search text or keys.

A **371,137,392-byte private backup** containing **8,127 files** was restored on Linux, every file hash checked, all record versions validated, and review4/review5 manifests retained. The temporary restoration was removed only after success. Backup SHA-256: `a469b5c17979b7bd893c79229983a05ac3372c2519fbdd3ac869b30e472e555d`. [Restoration receipt](backup-review5-20261028.json).

Known campaign estimates are **CNY254.26**, approximately **CNY21.38 more** than the previous checkpoint. The **CNY50.76 reserve for 104 uncertain outcomes** remains intact; other reservations total **CNY300.44**, including the prior browser-test hold. Conservative exposure is **CNY605.46 / CNY1,500**, within the owner-managed additional USD300-equivalent allowance. These are estimates, not a provider bill. No uncertain request was assumed free. [Usage receipt](usage-review5-20261028.json).

## Next bounded work

Prioritise 25 existing works, five per subject, by explanatory need and accessible evidence. High-priority gaps include Noether's algebra/symmetry contributions, probability-limit foundations, gravitational deflection, fragmented cross-work routes and deeper individual credit. Resolve the exact work and passage set before extraction; do not merely add more catalogue titles. Improve relevance judgments beyond title-based acceptance and add new frozen query cases before further retrieval changes. Reassess corrected routes and isolated insights independently, without an arrow quota.

No new paid batch is running or scheduled by this delivery. Broader corpus completeness and qualified human audit remain unfinished. Public deployment and GitHub publication await acceptance.
