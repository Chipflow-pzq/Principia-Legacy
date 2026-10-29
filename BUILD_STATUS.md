# Principia-Legacy 1.5 — current acceptance status

**29 October 2026 · reader 1.5.0 · atlas 1.5.0-exploratory.** The accepted review5 content is now deployed at [the public URL](https://atlas.chipflow.net/web/legacy/). The public snapshot preserves its scientific records unchanged; the new GitHub PR is reserved for manual merging by the owner. [Deployment verification and rollback](docs/DEPLOYMENT-1.5.md).

The Git source edition contains the complete 1.5 software and the existing 1.4.1 reference corpus. Counts below describe the full server dataset, not the smaller Git checkout.

Open **http://127.0.0.1:8767/** and search **neuronal group communication**. It now returns a real work with ten extracted insights and five individual contributors; its topic contains eleven insights and eight warranted relationships. The previously empty neuroscience entries have been populated from full-text evidence.

## Completion is not catalogue size

| Subject | Insights | Topics with content / listed | Works with insights / listed | Ready routes / 100 |
|---|---:|---:|---:|---:|
| Mathematics | 1,035 | 107 / 197 | 124 / 230 | 12 |
| Physics | 1,117 | 110 / 288 | 128 / 308 | 15 |
| Computer science | 1,342 | 98 / 214 | 117 / 230 | 12 |
| Economics | 1,011 | 97 / 180 | 112 / 188 | 6 |
| Biology & medicine | 1,195 | 97 / 275 | 112 / 280 | 4 |

**5,700 insights, 4,211 relationships, 1,154 registered topics, 1,233 works and 911 individually sourced profiles.** Only 593 works and 113 profiles have linked insights. There are 509 topics with any insights, 318 with at least eight, and **49 meeting the strict reading-route criteria**. There are 143 joint-premise relationships, four cross-subject relationships and 926 isolated insights. These counts do not certify scientific completeness.

The 1,000-insight milestone is numerically met in every subject. The 100-route milestone has **451 routes outstanding**. The longer-term 200-topic/2,000-insight target per subject remains. **640 works, 645 topics and 798 selected people lack extracted/linked insights.** Source-bound profile text is not a complete biography.

## Quality and retrieval

This repair retained **201 new insights**, independently machine-checked the new material, sampled 100 earlier insights and 150 earlier relations, withheld unsupported arrows, narrowed three neural claims, removed one duplicated restatement, and preserved every failed/rejected attempt. Strict ready routes fell from 50 to 49 after corrections; approvals were not carried across changed content. Missing links remain visible.

All **25,533 immutable versions** validate, with exact source/review pins for current visible records and no private passage-hash errors. All 1,154 topic neighbourhoods, five flagships, three tours, dependency closure and joint-premise caps pass the release integrity check. **15,627 mathematical spans render without KaTeX errors.** These checks do not establish scientific correctness.

The frozen availability set improved from **37 to 49 of 52 queries with content-bearing results**, with four negative controls empty. The separate 35-case retrieval benchmark retains hit@10 **0.9697** and MRR@10 **0.9545**. Warm server p95 is **60.03 ms** on the broader availability set, excluding network latency. Results can still be incomplete or loosely related; arbitrary-query recall is not established.

Search and topic cards now distinguish explanations from reading lists before opening. Coverage is visible per subject. Search-to-inspector return works on narrow screens, old snapshots can switch to the current atlas while preserving the query, and small maps show their complete initial neighbourhood. Currency and mathematical notation render separately. A database-build permission fault and overaggressive tunnel invalidation were repaired.

## Verified reader behaviour

The accepted repair passed **163 backend tests**; the publication branch passes **167**, including promotion, separate hosting data homes and hosted pagination. The final broad browser run passed **92 desktop/mobile workflows**, followed by **12 affected checks** after improving small-map labels and layout. Two real SSH/reader interruption tests recovered in about **4.5 seconds**, preserving the query without reload. Initial failing reports remain available. TypeScript, production build, targeted lint and installed-package checksum verification passed. No qualified human audit is implied by these checks.

First view: **2.703 seconds**. Local browser plus proxy: **732 MB RSS**; the remote service is measured separately at approximately **279 MB**. Zero external browser requests were observed; the backend still requires SSH networking. Server neighbourhood p95: **9.63 ms**. Network-inclusive sequential search p95: **1.159 seconds**; four-concurrent-search p95: **2.150 seconds**; seven sampled neighbourhoods: **1.298 seconds median / 5.506 seconds maximum**. The network-inclusive search and graph targets are not consistently met.

Release comparisons now request bounded pages, reducing the sampled first response from **1.72 MB to 34 KB**. The cloud reader ZIP is **1.49 MB**, installed contents **3.21 MB**, with 81 verified file checksums. Mac and Linux were exercised; Windows was not tested in this repair. See the full report for methods, retained failures and precise scope.

## Data and operations

The private server is authoritative for canonical files, source archives, model/index, jobs and receipts. SQLite is rebuildable: the private review index is **297.8 MB**, and the public-only index is **259.2 MB**. The installed local reader is about **3.2 MB** and keeps existing browser-local settings/maps. No new cloud corpus or encoder was downloaded to the Mac.

A **371.1 MB private backup with 8,127 files** was restored and checksummed on Linux; every immutable record validated and both recent snapshots survived. The restoration copy was removed after verification. Mac login startup and automatic SSH recovery remain enabled. Network access is required for the cloud preview. The older review3 offline package is retained and does not contain review5 data.

## Review and spending

**Qualified human review: zero.** A fresh stratified 100-insight/150-relation sample is prepared for human auditing. The existing research suite and live-exploration evaluations are historical evidence; no new paid personal-exploration test is claimed here.

Known campaign estimates: **CNY254.26**. Uncertain reserve: **CNY50.76** across 104 outcomes; other holds: **CNY300.44**, including the prior browser-test reservation. Conservative exposure: **CNY605.46 / CNY1,500**, within the additional USD300-equivalent allowance. This repair added approximately CNY21.38 in known estimates. These are not the provider bill; uncertain outcomes were neither cleared nor replayed.

## Next bounded batch

Resolve exact accessible sources for 25 important existing works, five per subject; prioritise missing foundations, individual credit and fragmented routes over catalogue growth. Noether, probability-limit explanations and gravitational deflection remain visible priorities. Independently assess connection warrants and improve relevance evaluation beyond availability counts. Do not add arrows to satisfy a quota. No paid batch is currently running or scheduled.

[Full completion and verification report](reports/coverage-review5-20261028.md) · [Local review instructions](docs/LOCAL_PREVIEW.md) · [Earlier checkpoint](reports/build-status-before-review5-20261028.md)
