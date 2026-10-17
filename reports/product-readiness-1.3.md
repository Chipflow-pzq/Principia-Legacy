# Local product acceptance — 1.3

**17 October 2026 · reader 1.3.1-rc.2 · atlas 1.3.1-exploratory.** This report describes the local candidate, not the public deployment. No remote push or deployment was performed. [Machine-readable results](product-readiness-1.3.json).

## Readiness is four separate questions

| Dimension | Evidence and limit |
|---|---|
| Software | Python, browser, hosted-prefix, integrity, correction and offline checks pass. The build is available for local acceptance. Windows, Linux and production load remain untested in this session. |
| Coverage | 2,880 visible insights, 1,920 relationships, 268 source identities; 182 of 184 topics populated. Thirty new foundation topics and 213 net new insights. Expanded targets remain unmet. |
| Machine screening | All visible contributions and relationships have an accepted check pinned to their exact revision. Automated scientific judgments remain fallible. Personal maps are unverified drafts, separate from the corpus. |
| Human review | **Zero qualified human audit.** A stratified queue of 100 insights and 150 relationships is prepared, with adjudication fields empty. Primary-agent editing is machine work, not human review. |

## What changed

Ordinary navigation and old preview bookmarks now reach the same installed application. Personal exploration uses `/#page=explore`; topic and insight links retain reproducible content snapshots. Settings distinguishes the reader version from the atlas edition. Switching between Browse and Trace preserves the user's context.

Exact title search ranks ahead of incidental text matches. Contribution inspectors preserve search navigation, link to containing topics, distinguish unknown attribution and expose current review state. Inline and display mathematics use local KaTeX. Connection filters retain the graph and positions. A synchronized list and keyboard controls work at desktop and narrow widths.

Storage uses bounded snapshot caching and smaller topic queries. The code keeps one graph renderer, ordinary React state, a standard-library reader and a separate authoring pipeline. The provider adapter separates answer limits from streaming metadata, bounds concurrency and repair, preserves completed verdicts and makes unknown charges explicit. Four focused literature searches avoid redundant publication lookups; direct foundation and mechanism retrieval remains in place.

## Corpus work

All **2,233** previously visible relationships were audited: **1,747 retained, 23 repaired, 463 withheld**. New exact-revision reviews accompany retained/repaired claims. Endpoint corrections triggered dependent rechecks, rather than carrying approvals onto changed content. Five source-context follow-ups were incomplete and remained withheld.

The expansion covers six foundation assignments in each subject. Seventy-one editorial exclusion decisions removed or withheld unsupported, misleading, duplicate or low-substance candidates. Corrections include CLT normalization and scope, binary-counter amortization, reduction direction, monodromy invariance, Darwin/Wallace independence, population-genetic assumptions and two incorrect source locators found in a stratified 200-contribution machine sample. The sample returned 198 supported records; it is not an estimate of expert-reviewed accuracy across the entire corpus.

All **14,218 immutable versions** remain available. The final snapshot is `1c7e874593a7d883d25835befbaf5e236f82bd6fdfa13da5dfdc9bfed8e7621c`. Intermediate 1.3.0 and earlier releases remain reproducible.

| Subject | Populated topics | Unique primary-subject insights | Remaining topics / insights |
|---|---:|---:|---:|
| Mathematics | 36 | 564 | 164 / 1436 |
| Physics | 37 | 537 | 163 / 1463 |
| Computer Science | 37 | 639 | 163 / 1361 |
| Economics | 36 | 519 | 164 / 1481 |
| Biology Medicine | 36 | 621 | 164 / 1379 |

Targets are 200 populated topics and 2,000 insights per subject. The original 3,000-relationship lower target is short by 1,080. C1002 (computability) and M2004 (linear-algebra foundations) remain empty assignments. **600 isolated topic memberships across 147 topics** still lack an admitted relationship within their topic. Shared membership counts an insight only once in corpus totals. No edge was manufactured to eliminate these gaps.

Detailed records: [coverage](coverage.json), [relationship decisions](atlas-1-3-typed-arrows-applied.json), [editorial exclusions](atlas-1.3-editorial-decisions.json), [contribution sample](atlas-1.3-contributions-audit.json), [primary corrections](atlas-1.3-primary-corrections.json), [dependent rechecks](atlas-1.3-dependent-rechecks.json), [human-audit queue](audit-sample.json).

## Real browser tests

These are the six user-requested **development and acceptance examples**, not held-out research. Each used the real form, live source retrieval and the exact selected model **deepseek-ai/DeepSeek-V4.1-Flash**. No substitution or fabricated response was used. Both insight and arrow inspectors were exercised where those records were present. [All attempts and usage](product-readiness-1.3-live.json).

The structural criterion requires one requested result, a relevant foundation, a reachable explanatory core containing at least four ideas and two non-teaching connections, with at least 80% of nodes connected. Joint premises must all be accounted for. This is a structural diagnostic, not proof that the statements or warrants are correct. Timing requires a first visible insight within 60 seconds and completion within 180 seconds.

| Query | Finished in | Insights / links | Structural target | Timing target |
|---|---:|---:|---|---|
| lithography machines for chip | 145.1 s | 6 / 6 | Not met | Met |
| Plasma-enhanced chemical vapour decomposition | 156.3 s | 10 / 10 | Met | Met |
| resuable rocket | 105.7 s | 7 / 7 | Met | Met |
| GPU and cuda | 107.4 s | 5 / 4 | Met | Met |
| Alphafold | 120.6 s | 6 / 3 | Not met | Met |
| large language models such as chatgpt | 149.1 s | 7 / 5 | Met | Met |

The current matrix completed 6 of six checks; 4 met the structural criterion and 6 met both timing targets. Earlier failures remain recorded, including missing core routes, disconnected ideas, long waits, classification mistakes and an input-copying response. A short successful sample does not establish a production success rate.

### Primary-agent inspection of generated content

- **lithography machines for chip:** Six ideas and six arrows were returned, but the checker demoted the scanner-operation endpoint to a supporting idea, so the required route criterion failed. The wavelength-only resolution phrasing also oversimplifies the optical and process assumptions. This is a useful partial explanation, not a complete ancestry map.
- **Plasma-enhanced chemical vapour decomposition:** The graph connects electric force and ionization through discharge, energetic electrons and deposition. It meets the structural criterion, but two carbon-radical deposition cards substantially repeat each other. The carbon-growth example is correctly scoped to its source and must not be read as a universal PECVD mechanism or chronology.
- **resuable rocket:** Momentum conservation, the rocket equation, retrograde burns and recovery form a recognizable path. However, one warrant says propellant is expelled opposite the motion while explaining deceleration; the sign/direction needs correction. The restart/throttle title extends beyond the cited multi-engine description, and a simulated landing-controller example does not establish the control algorithm used by a named launcher. Structural success is not scientific acceptance.
- **GPU and cuda:** Data parallelism, threads/blocks/grids and kernel execution provide a useful short route. The memory-management card uses universal language that exceeds a scoped description of explicit-memory CUDA programming, and the compiler/toolchain card is isolated. This map should not be treated as a complete account of CUDA memory models or GPU architecture.
- **Alphafold:** The map identifies sequence-based structure prediction, evolutionary information and the Evoformer, but lacks a retained general foundation and a connected explanation of the main mechanism. The alignment-depth bound needs to stay tied to the reported AlphaFold generation and evaluation, rather than all later systems. It fails the structural criterion.
- **large language models such as chatgpt:** Conditional probability and maximum likelihood connect to autoregressive language modeling and a scoped decoder-only generation endpoint. The bounded refinement restored that endpoint, and the graph meets the structural criterion. It still conflates words with tokens in several cards, includes an isolated historical neural-network summary, and does not establish a complete training or attribution history. Claims about the representative GPT-style branch do not identify the undisclosed architecture of every current ChatGPT model.

These are machine editorial assessments, not qualified human scientific auditing. Source excerpts and model critics can share errors or oversimplifications. Reference works support scoped explanations; they do not establish priority or a complete history. Generated maps stay labelled **Personal draft · not verified**, and unresolved routes stay visible. They are never admitted automatically to the published corpus.

## Software and offline verification

- **106 Python tests passed.** The final browser run passed **287 tests**, with 3 intentional project skips and zero unexpected failures. The skips cover desktop-only canvas geometry, exhaustive topic traversal and performance measurements; other mobile reading/interaction tests ran.
- **Two hosted-prefix tests passed**, one desktop and one mobile viewport. Assets, search, profiles, private-query boundaries and reload stay under `/web/legacy/`.
- TypeScript including unused declarations, Python undefined-name checks, exported schemas, identifiers, anchor/revision resolution, neighborhood limits, joint premises, immutable snapshots, correction propagation and source-closed exports passed.
- **8,658 formula render checks passed** for the current visible content. Four warnings remain in superseded immutable historical versions; current content contains no detected formula failures.
- The extracted-reader smoke test runs with Python `-S`, denies outbound socket connections except loopback, and checks every bundled asset plus the principal read APIs. Browser reader tests independently block external requests. This is application-level network denial, not an OS firewall claim. Personal research is explicitly online.
- Security tests exercise parameterized search, restricted file serving, unsafe URL/HTML rejection, bounded source acquisition, private-address rejection, inert XML and prompt-injection fixtures. Browser runs detected no private research query, API key or generated map sent to the atlas server. Explicit local save/download behavior was tested separately.

### Performance on this machine

Warm loopback HTTP measurements use 30 samples after warmup. Search p95 is **38.67 ms**, neighborhood p95 **84.93 ms**, and topic-list p95 **279.41 ms**. First-view and process-memory observations, including their measurement scope, are in [the performance report](performance.json). First view was **1,160 ms**. Browser-plus-reader summed RSS was **1.11 GB**; the earlier long-session observation was **1.18 GB**. RSS may count shared pages more than once, but the approximate 1 GB memory target is not claimed as met when the measured sum exceeds it. The reader was not restarted to reduce this measurement. These are local measurements, not WAN latency or a concurrent-public-load benchmark.

Only **macOS x86_64** was executed here. Chrome mobile viewport emulation is not a physical-phone test. Cross-platform launchers and CI are supplied, but Windows and Linux are not claimed as tested. The frontend build emits a large-chunk advisory; the measured first-view performance is recorded, and no unnecessary component or global-state framework was added.

## Usage and research limits

Authoring receipts record **1742 attempts**, 1653 successful requests, 53 unknown possible charges, and one historical interruption marker covering up to four additional in-flight requests. Reported totals are **31,124,084 input / 3,697,818 output tokens**. The dated-rate known subtotal is CNY 108.667; it excludes 593 unpriced requests and all unreported usage, so it is not the full cost.

Browser development/acceptance adds **485 provider requests** across 29 attempts. Its separate receipts report 2,302,362 input / 398,715 output tokens; 0 requests have no captured usage and may still be charged. No exact account bill or hard enforcement of the owner-managed US$300-equivalent allowance is claimed. Private source packets and generated QA maps are excluded from the public package.

A separate six-request same-input output-format diagnostic used 22,656 input / 3,868 output tokens, additional to both totals above. Three schema-mode and three JSON-object responses all classified the scanner endpoint correctly. The earlier contradictory verdict was not reproduced, so the comparison does not establish a decoding-format cause or justify a model substitution. Six preliminary TLS failures occurred before HTTP submission and are separately recorded. [Diagnostic receipts](product-readiness-1.3-verdict-formats.json).

The earlier research pilot was **not rerun** for this candidate: 120 frozen synthetic cases, 30 development/90 held out, five conditions, 599 responses from 600 attempts. Typed-atlas verdict agreement equaled flat retrieval at 66.7%; boundary removal scored 59.2%; typed correction uptake was 25%. Exact input-token equality and independent expert gold labels remain outstanding. The unchanged pilot does not establish improved scientific accuracy or alignment. [Protocol](../docs/EVALUATION.md).

## Acceptance decision

**The reader and corpus are ready for local review; autonomous Trace is not certified for unattended public research.** The final matrix still contains incomplete routes and scientific-scope defects, despite completed software checks. The six development examples do not establish a dependable success rate, and the current lightweight model critique does not catch every wrong warrant. Further work must improve evidence selection and calibration of claim/role judgments before claiming that all requested graph-quality criteria are met. This is an unresolved product limitation, not a reason to hide rejected links or lower the criterion.

## Delivery and next boundaries

The source archive and offline distribution are prepared for local acceptance. Archive checksums, installed/download sizes, clean extraction, offline restoration and secret exclusion are recorded in the delivery report beside the archives. No API credential, private cache, browser profile or personal map belongs in either package.

Before treating this as an authoritative scientific resource, complete qualified human auditing and resolve the recorded content gaps. Before broader public use, test the intended Linux/server configuration, network path, concurrency and operational limits. Those are separate from this local acceptance run. No deployment or GitHub publication occurred here.
