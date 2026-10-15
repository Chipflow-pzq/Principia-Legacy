# Principia-Legacy 1.2 release report

**1.2.0-exploratory** adds shared-topic navigation, continuous search, searchable scientist profiles and classical foundations. It is a tested local reader with an incomplete, machine-screened corpus. The expanded project is not finished.

| Dimension | Actual result |
|---|---|
| Software | Read-only offline reader; search across ideas, topics and people; preserved reading context; shared-topic and source navigation; existing graph, comparison, correction and export workflows |
| Corpus | **2,667 visible insights, 2,233 relationships, 237 source records**; 154 registered topics, **152 populated**, 71 meeting the implemented initial-neighborhood checks (at least eight insights, an admitted endpoint and recorded alternative/limitation/attribution searches) |
| Growth from 1.1 | **846 additional visible insights, 610 additional relationships, 92 additional sources**; old records and releases preserved |
| People | **29 source-linked research profiles**, within 679 searchable person, team and attribution pages. An attribution index entry is not a researched biography. |
| Machine screening | Exact-revision passage-grounded checks for every visible contribution and relationship; editorial triage and explicit immutable corrections |
| Human review | **None**; a newly stratified 100-insight/150-relation audit queue is prepared, with human judgment fields blank |

## Reading experience

Search now shows separate idea, scientist and topic matches. Opening an insight preserves the results, query and page; previous/next controls, Back to results, browser history and reload keep the reading context. Scientist-directory queries also survive profile navigation. Delayed startup is tested so early clicks do not invent a nonexistent working snapshot or lose a trace.

Every insight inspector exposes its containing topics under **Explore this idea in**, including shared topics across subjects. Topic membership is a navigation claim, separate from historical influence or logical dependence. Ten additional shared routes have explicit reasons and revision-pinned evidence. Source or insight corrections invalidate affected memberships; older releases retain their original links. Evidence briefs include membership anchors and the corresponding source versions.

The **Scientists** directory provides sourced research descriptions where researched, related ideas, topic links and original credit notes. Team credits are resolved only for explicitly documented source bylines. Unresolved names remain separate attribution pages; initials or similar names are not automatically merged. Independent discoveries remain distinct contributions.

Hamiltonian mechanics, general relativity, information theory, calculus, mechanics, evolution, inheritance and economic foundations are now directly searchable. Einstein's 1923 account is labeled as a dated historical argument; later experimental evidence remains separately attributed. Secondary textbook exposition does not establish original discovery priority.

Bundled KaTeX, sticky subject navigation, keyboard access and responsive reading are retained. The topic catalog is paginated; source assignments without admitted insights remain visibly incomplete.

## Coverage and quality limits

The working minimum is **200 populated topics and 2,000 unique primary-subject insights per subject**. It is not met. Shared memberships do not multiply insight counts.

| Subject | Populated topics | Unique insights | Remaining topics / insights |
|---|---:|---:|---:|
| Mathematics | 30 | 516 | 170 / 1484 |
| Physics | 31 | 499 | 169 / 1501 |
| Computer Science | 31 | 601 | 169 / 1399 |
| Economics | 30 | 483 | 170 / 1517 |
| Biology Medicine | 30 | 568 | 170 / 1432 |

The original 3,000-relationship lower target remains short by **767**. No links are added merely to connect the graph. Most added topics are bounded first source passes, not complete historical reconstructions. Depth-six ancestry, broad alternatives, original-priority research and many frontier endpoints still need evidence. Turing's source download timed out; the first linear-algebra assignment resolved to navigation rather than adequate claim text. These two topics remain empty with explicit gaps.

Editorial correction withheld 23 padded, routine or attribution-problematic contributions and quarantined 22 dependent relationships. Separate historical-scope corrections rechecked Einstein-related interpretations. Earlier failed or over-restrictive editorial attempts are retained for inspection; they are not silently presented as successful checks. Four calibrated reuse candidates were admitted as distinct insights; no real shared reuse was accepted in that calibration. A positive synthetic pipeline test separately verifies safe reuse, source closure and correction invalidation.

OpenStax source rights are recorded per retrieved edition, including CC BY-NC-SA 4.0 where applicable. Third-party full texts are not shipped. Original project explanations are CC BY 4.0; code is MIT. Source authors retain their rights.

## Verification

- **65 backend tests passed**; **46 full-suite browser tests passed**, with two intentional duplicate mobile skips. Two additional delayed-startup regression checks passed on desktop and mobile.
- **10,648 immutable versions** passed exported schemas and integrity checks. All 154 topic pages were exercised by the desktop traversal. Five flagship endpoints, three tours, source closure, joint premises and the 200-node cap passed acceptance checks.
- **5,404 mathematical expressions** parsed with zero KaTeX failures. Parsing and machine equivalence screening are not specialist verification of mathematical truth.
- Actual disposable corrections to all five flagship endpoints verified stale approval invalidation, dependent rechecks, coverage/export updates and preserved historical snapshots. Shared-navigation corrections are separately tested.
- Offline tests deny non-loopback socket connections and inspect all bundled assets plus reader APIs. Browser tests block external requests. No background external requests or page errors were observed.
- Source acquisition limits, private-address blocking, unsafe URLs, SQL parameterization, restricted static serving, prompt-injection fixtures and credential exclusion are covered by implementation checks and tests.
- Only **macOS** was executed. Windows/Linux launchers and CI are supplied, but not locally tested. Mobile checks use Chrome emulation, not a physical phone.

First view was **1.088 seconds**; warm search p95 **106.08 ms**, neighborhood p95 **580.74 ms**, and full topic-catalog p95 **1293.46 ms**. Summed Chrome/reader RSS was **1.066 GB**, slightly above the approximate 1 GB planning target; shared pages may be counted twice. Measurements were taken on the actual machine, with the full browser suite running. These are not guarantees for the much larger planned corpus.

## Research, usage and continuing work

The original 120-case synthetic pilot is preserved: 30 development and 90 held-out cases, five conditions, 600 attempts and 599 responses. Typed-atlas verdict agreement equaled flat retrieval at 66.7%; boundary removal scored 59.2%; typed correction uptake was 25%. Exact matched input-token budgets and independent expert gold labels remain outstanding. The pilot does not establish scientific accuracy or improved alignment.

Cumulative receipts record **1149 attempts**, **1060 successful**, **53 unknown-charge interruptions/timeouts**, and an older marker for up to **4 additional unreceipted requests**. Reported usage is 21,009,312 input and 3,169,805 output tokens. The known-token planning subtotal is **CNY 108.667**, using documented daytime rates before discounts and excluding unknown usage. This is not an account bill. The US$300-equivalent allowance remains manually managed.

The next frozen source curriculum contains **1,105 candidate assignments in 45 batches**, after removing nine navigation/index entries from the original scouting plan. These are planned sources, not admitted knowledge. The resumable runner uses at most four concurrent requests, extraction and separate criticism, existing-insight retrieval before and after extraction, Pro editorial triage, bounded repairs, receipts and a checkpoint after each completed batch. It pauses on excessive source/provider failures or conservative spending signals. Authoring requires explicit credentials/network flags; browsing never does.

The campaign's live state is in `reports/campaigns/foundations-curriculum-1-2-v2.json` and `BUILD_STATUS.md`. Published 1.2 remains reproducible while subsequent validated batches enter the working snapshot. The large coverage request, expert review and deeper ancestry remain ongoing work.

## Distribution

Use `dist/principia-legacy-1.2.0-exploratory.zip` for the offline package or the sibling `-source.zip` for source with prebuilt assets and offline database restoration. Extract and run `python3 start.py` (Windows: `py -3 start.py`). No Node.js, API key, GPU or online installation is needed for reading.

Per-file checksums are included. Archive hashes, exact sizes and clean-extraction/startup results are recorded beside the archives in `principia-legacy-1.2.0-exploratory-verification.json`. Only the delivered archive and its external verification receipt define the packaged artifact. No remote repository or GitHub release was published.
