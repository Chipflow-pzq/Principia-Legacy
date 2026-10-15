Current release: [1.2.0-exploratory](RELEASE-1.2.md). The report below is the preserved 1.1 account.

# Principia-Legacy 1.1 release report

**1.1.0-exploratory** is a locally runnable upgrade with a substantially broader corpus and a revised reader. Software readiness, coverage, machine screening and human review are separate claims. The founding proposal is not yet fully completed.

| Dimension | Verified result |
|---|---|
| Software | Offline read-only reader; graph/list, source and arrow inspectors, search, tracing, comparison, limitations, version comparisons, correction workflow and evidence export |
| Corpus | **1,821 contributions, 1,623 relationships, 145 sources**, across five subjects and all 60 populated topics |
| Growth from 1.0 | **1,004 additional visible contributions, 876 additional relationships and 81 additional sources**; original 1.0 snapshot retained |
| Coverage | Contribution count is within the 1,500–2,500 target. Relationships remain **1,377 below** the lower 3,000 target. Counts do not measure completeness or historical depth. |
| Machine screening | Exact-revision source-grounded reviews on every visible contribution and relationship; additional editorial triage of all 1,014 proposed new contributions and Pro escalation of 88 cross-source warrants |
| Human review | **None**; the stratified 100-contribution/150-relation audit is prepared, with all human adjudication fields blank |

Five flagship maps, three cross-disciplinary reading tours and **72 attributed normative arguments** are included. Tours and idea families are navigation aids, not asserted historical influence or merged discoveries.

## Reader improvements

- Bundled KaTeX renders inline/display equations throughout the reader. Source-preserving notation overlays improve older text without rewriting archived claims.
- The subject sidebar remains available while scrolling; narrow screens use compact sticky subject navigation.
- “Subjects,” “topics,” and “Explore a discovery” replace unclear navigation terminology. Each flagship offers a direct route to its main result.
- Comparison includes its own search and suggestions. Saved links and Back/Forward preserve the reading context; keyboard focus enters inspectors and returns to the opener.
- Topics initially show 40 ideas, with progressive expansion up to 200. The main result stays included, existing positions remain stable, and Overview/Focus controls keep dense maps usable.
- Joint-premise relationships list all necessary premises together. Loading states are distinct from empty filtered maps.

## Evidence quality and corrections

The stricter connection review supported 52 of 88 proposed cross-source warrants and rejected 36. Rejected warrants were held through new revisions. Ten contribution accounts were also held for duplication, scope, attribution or date issues; their dependent interpretations were marked for recheck. These changes left **1,623 visible relationships**, without inventing links to improve connectivity. Two editorial exclusion recommendations were declined with recorded reasons because the compared records had distinct claims or source scopes. Machine judgments are fallible and are not human auditing.

All new source assignments and completed batch outcomes are reproducible. Failed acquisitions, abstentions, editorial format failures and their bounded repairs remain in reports. The legacy helpers that rewrote canonical versions were retired; supported admission is append-only and corrections require explicit patches. Earlier releases and the frozen evaluation baseline are preserved.

## Verification

- **55 backend tests passed.** The full browser suite passed **36 tests**, with two intentional mobile skips. Five focused checks passed after the final loading-state polish, with one intentional duplicate mobile-performance skip.
- **7,368 immutable record versions** passed exported JSON Schemas and semantic integrity checks. All 60 topic pages and available main-result inspectors opened in the desktop browser check.
- **2,472 mathematical expressions** parsed without KaTeX errors. Notation conversion used exact-span changes and separate machine equivalence screening; mathematical correctness still depends on source and specialist review.
- Disposable corrections to all five actual flagship endpoints verified dependent rechecks, coverage/brief updates, new-approval requirements and unchanged historical snapshots.
- Standard-library reader tests denied non-loopback sockets. Browser tests blocked external page requests; no background external requests or page errors were observed.
- Desktop and narrow-screen layouts were visually inspected. **Only macOS was executed here**; narrow-screen tests use Chrome emulation. Windows/Linux launchers and a three-platform backend CI workflow are supplied, but those platforms were not run locally.

On this machine, first view was **0.587 seconds**, warm search p95 **40.48 ms**, and neighborhood p95 **155.14 ms**. Summed reader/Chrome RSS was approximately **929 MB**, potentially counting shared pages more than once. These measurements apply to this corpus and machine.

The offline and source archives contain checksums and are verified by clean extraction, startup and offline restoration before delivery. Exact sizes and archive hashes are in the accompanying distribution reports. Python 3.12+ is the only reader prerequisite; no Node.js, API key, GPU or online installation is needed.

## Research and usage

The preserved synthetic pilot contains 30 development and 90 frozen held-out cases across six families, under five conditions: **600 attempts, 599 responses**. Typed-atlas verdict agreement equaled flat retrieval at 66.7%; boundary removal scored 59.2%. Typed correction uptake was 25%. These are rule-based instrumentation outcomes, not expert measures of scientific accuracy. The pilot used paraphrases and character ceilings; the stricter matched-evidence/input-token-controlled study remains outstanding. No improved-alignment claim is supported.

Cumulative receipts record **755 provider attempts**, including 666 successful attempts and 53 interrupted/timed-out attempts with unknown possible charges. A separate interruption marker records up to **4 additional in-flight requests without individual receipts**. Reported totals are **15,926,840 input and 2,335,997 output tokens**. Missing usage is not free. The US$300-equivalent allowance remains owner-managed; these receipts are not an exact monetary bill or hard spending enforcement.

## Remaining coverage

All 60 topics contain contributions; 51 have an admitted endpoint and initial neighborhood. Nine still lack an admitted endpoint: **M01, P07, P09, P11, C09, E03, E08, B10 and B11**. Their foundations remain browsable. Some topics contain fewer than 20 contributions; source completeness and precise attribution take priority over filling quotas. Complete depth-six ancestry, independently verified current-frontier relevance, the stricter controlled research study and qualified domain review remain outstanding.

See [coverage](COVERAGE.md), [upgrade review](UPGRADE_REVIEW.md), [implementation scope](IMPLEMENTATION_STATUS.md), and [research limitations](EVALUATION.md). Run `python3 start.py` from the extracted directory, then open `http://127.0.0.1:8765`. No remote repository or GitHub release was created.
