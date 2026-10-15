# Reader and corpus review for 1.1

The 1.0 archive is a runnable exploratory release, not completion of the founding proposal. This review uses the executable proposal and the actual reader. The archived 1.0 content has 817 contributions, 747 relationships and 64 sources, with ten empty topics. A single-source collection is insufficient to reconstruct the history of an idea, even when many cards have been extracted from that source.

## Reader corrections

| Finding | Change | Verification |
|---|---|---|
| Mathematical expressions appeared as plain text | Bundled KaTeX handles inline and display delimiters throughout search, lists, inspectors and comparison. Exact-text presentation overlays typeset older notation without rewriting archived claims. | Corpus-wide KaTeX parse check; independent machine notation-equivalence pass; browser rendering and injection fixtures |
| Subject navigation disappeared during scrolling | Sticky desktop subject rail and compact sticky horizontal navigation on narrow screens | Scroll-position tests at desktop and mobile sizes; visual inspection |
| The five starting paths did not explain their purpose | “Explore a discovery,” plain-language names, a direct explanation, and “Start with the main result” inside a topic | Reader inspection and endpoint navigation tests |
| Unfamiliar terminology obscured basic navigation | “Subjects” and “topics” in the interface; familiar relationship labels, with precise predicates retained in the data | Visible text checks; shared semantic mappings |
| Comparison required closing the panel to find another idea | Search and current-map suggestions inside the comparison panel | Two-idea comparison and evidence navigation tests |
| Browser history did not restore reading context | Saved topic/contribution URLs, Back/Forward restoration and stale-response cancellation | Back/Forward and pinned historical-release tests |
| Map interactions repeatedly changed the view | Layout updates are keyed to record identities and revisions; progressive expansion preserves positions and camera; readable initial focus with explicit overview control | Browser graph inspection and progressive-expansion checks |
| Larger topics hid ideas beyond the initial response and could omit their main result | Endpoint-first topic views, a visible count and “Show more ideas”; initial 40 nodes, capped at 200 | Prefix/endpoint integrity test and desktop/mobile expansion checks |
| Long provider outputs were rejected because SSE overhead consumed the content cap | Bound transport bytes and decoded model text separately; persist attempt receipts before transmission; retain interruption uncertainty | Synthetic stream-overhead and missing-completion tests, followed by resumed source passes |
| Quarantined main results could leave a broken inspector action | Topic responses omit unavailable endpoints while retaining their declared identity for diagnosis | Real correction workflow and endpoint-availability regression test |
| Early navigation could be overwritten by loading | User navigation wins over initial-link restoration; initial loading does not clear a typed search | Search, release comparison and navigation regression tests |

## Content expansion and preservation

Source assignments are frozen before execution, including their explanatory purpose, parent endpoint, depth and checklist. The new `expand` command uses four workers, resumable receipts, separate source-fidelity criticism and append-only admission. An assignment is a research task; it does not assert a historical link. Existing record versions and frozen manifests cannot be replaced by a new source pass. Revision conflicts are held for an explicit patch.

Expansion covers missing topics, foundational contributions, alternatives and limits. Cross-source connections are proposed and checked separately against exact cached source versions and passage hashes. A bibliography entry, chronology, or similar vocabulary does not establish influence. Duplicate endpoint/predicate connections are excluded; independent formulations remain distinct. No connections are added for visual density.

Two first-release bridge helpers that could rewrite canonical versions are retired with an explicit migration message. The supported connection tools append records or produce review reports, and corrections use new revisions.

The legacy curation merge now inspects the whole canonical corpus and appends new versions instead of rewriting a base file. This prevents a later curation run from duplicating expansion batches or deleting historical records through admission exclusions. Old approvals remain attached to their exact content hashes.

## Remaining proposal gaps

- A source-complete initial neighborhood is not complete ancestry. Source acquisition failures, unresolved historical dependencies and attribution questions remain explicit. Current relevance has not been independently certified for every frontier.
- The content and relationship targets remain admission-independent. Final counts and shortfalls are computed in `BUILD_STATUS.md` and the release report.
- The six-family, 120-case research pilot is synthetic. It uses common character ceilings, not equal input token counts or identical raw-passage evidence. Its unfavorable and missing outcomes are preserved. The stricter controlled research study remains outstanding.
- The stratified 100-contribution/150-relation audit is prepared for qualified reviewers. No human audit has been performed, and no machine judgment is labeled human review.
- Windows and Linux launchers are supplied. This upgrade is exercised on macOS; other-platform execution remains unverified locally.

Final verification evidence is in the packaged reports. This document describes what each check establishes and does not replace those measured outcomes.

The completed 1.1 quality pass checked all 1,014 new candidate contributions editorially and escalated 88 cross-source warrants to Pro. It held 36 warrants and ten contribution accounts through immutable corrections. Two mistaken editorial exclusion recommendations were declined with recorded scope comparisons. Final admitted counts are 1,821 contributions and 1,623 relationships. Nine unresolved endpoints remain visible as gaps. See `reports/expansion/quality-correction-1-1.json` for precise decisions.
