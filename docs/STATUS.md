# Status of this source edition

**Prepared 15 October 2026.** The public demonstration and this repository use the frozen **1.2.0-exploratory** corpus. The cloud reader's five runtime modules match the released source, and its hosted adapter is included under `hosting/`.

| Dimension | Current evidence |
|---|---|
| Corpus | 2,667 visible contributions, 2,233 relationships, 237 source records |
| Coverage | Five subjects; 154 registered topics, 152 populated; two empty evidence gaps |
| Entry points | Five flagship maps, three guided cross-disciplinary journeys |
| People | 29 sourced research profiles within 679 searchable person/team/attribution pages |
| Machine screening | Exact-revision, source-grounded checks on visible contributions and relationships |
| Human review | No qualified human audit; a stratified 100-contribution/150-relation queue is prepared |
| Software | Complete local reader, authoring CLI, canonical records, prebuilt frontend and optional hosted adapter |

The planned minimum of **200 populated topics and 2,000 unique primary-subject insights per subject is not reached**. Shared topic membership never multiplies insight counts. The original 3,000-relationship lower target is short by 767. Full historical ancestry and broad disciplinary coverage remain open work; [COVERAGE.md](COVERAGE.md) lists the actual topic gaps.

## Verification

The original 1.2 release passed 65 backend tests, 46 browser tests plus two delayed-startup checks, offline startup, five flagship correction checks, 10,648 immutable-version schema checks, and 5,404 formula parsing checks. See [the dated release report](RELEASE-1.2.md) and `reports/1.2.0-verification-summary.json` for that original evidence.

This source edition adds a reproducible hosted-prefix build, public hosting code/tests, organized documentation and publication hygiene. Its new checks and package verification are recorded in `reports/github-source-verification.json`. Do not interpret the original release results as tests of every later code change.

## Research scope

The 120-case synthetic pilot has 30 development and 90 held-out cases across six families. Its five conditions produced 599 responses from 600 attempts. Typed-atlas verdict agreement equaled flat retrieval at 66.7%; boundary removal scored 59.2%; typed correction uptake was 25%. Exact input-token matching and independently expert-adjudicated gold labels remain outstanding. These results do not establish improved alignment or scientific accuracy. [Protocol and limitations](EVALUATION.md).

## Unreleased work

The separate local curation campaign completed one of 45 batches before stopping during the next batch's editorial check on 13 October. Its later working records are not included in this frozen source edition. The original development directory retains that work and its failure receipts. Archived plans in `config/` are research inputs, not completed knowledge and not running jobs.

No paid provider calls, live-site changes, remote repository creation or GitHub publication are part of preparing this source edition. Further curation, independent human review and deeper historical reconstruction remain separate work.
