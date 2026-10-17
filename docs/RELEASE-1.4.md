# 1.4 — Works, people and connected ideas

**Reader 1.4.1 · atlas 1.4.1-exploratory · 17 October 2026.** Accepted for publication. The scientific snapshot is unchanged from the accepted local build.

The earlier acceptance reports retain their original candidate versions and test context. See [deployment and publication](DEPLOYMENT-1.4.1.md) for the production record.

Browse a subject, open a topic, inspect a work and follow its specific insights.
The same idea can be read in more than one work, and a work can appear in several
topics. Original discovery credit and the evidence explaining an idea remain
separate. Work connections expose the checked insight relationship behind them;
shared membership alone does not create an influence claim.

Search presents **topics, works, ideas, and scientists/contributors** together.
Small spelling errors, accents, explicit name aliases and curated related concepts
are handled locally with bounded SQLite search. Search context survives opening a
work, profile or insight, reloading, and returning to the results. There are no
embedding downloads or provider requests for catalogue search. Discovery examples
follow the selected subject; All subjects gives a cross-disciplinary selection.

The contributor directory now uses explicitly selected individuals with sources
and selection reasons. An entire paper byline can no longer become a person.
Turing and von Neumann have linked original works and passage-grounded insights;
other additions include prize recipients, computing pioneers and a historical
supplement. The source selection and inaccessible pages are recorded in
[acquisition receipts](../reports/catalog-1.4-acquisition.json).

## Actual coverage

**882 works · 899 individuals · 781 registered topics.** Of these, **262 works**
and **184 topics** contain extracted insights. **620 works** remain a documented
extraction backlog. The scientific collection contains **2,905 insights and 1,941
checked relationships**, including 25 net new insights and 21 relationships from
the original Turing and EDVAC texts. There are 2,906 work–insight memberships and
36 scoped work connections. Membership never multiplies unique insight counts.

| Subject | Catalogued works | Selected people | Works with insights | Unique insights |
|---|---:|---:|---:|---:|
| biology medicine | 214 | 287 | 50 | 621 |
| computer science | 164 | 129 | 57 | 664 |
| economics | 124 | 110 | 51 | 519 |
| mathematics | 157 | 113 | 53 | 564 |
| physics | 225 | 270 | 51 | 537 |

People and works can span subjects; column totals can therefore overlap. The
suggested 200–500 selections per field are not achieved in every field. The much
larger goal of 200 populated topics and 2,000 insights per subject remains unmet.
Prize and institutional records also introduce selection biases. The next work
is deeper extraction from this source-backed library, plus missing industrial,
regional and historical foundations—not claiming that metadata is a completed map.

## Evidence and corrections

The primary agent reviewed selections and important scientific moves. Flash
assisted metadata normalization and source extraction; Pro assisted difficult
checks. A model's affirmative verdict was not accepted without inspecting its
rationale: a shared sphere-packing membership required a corrected density
normalization. Computing-origin refinements distinguished countability from an
effective enumeration and corrected reduction direction; four implementation
inventories were withheld. The final browser reading caught one remaining reversed
reduction phrase. Atlas 1.4.1 corrects it and rechecks both dependent relationships;
the earlier frozen 1.4.0 snapshot remains reproducible.

All of this is **machine/agent review, not qualified human auditing**. Zero
contributions have recorded human review. A separate 100-insight/150-relationship
audit queue remains prepared and unadjudicated.

See the [acceptance report](../reports/product-readiness-1.4.md) for actual tests,
latency, memory, offline restoration and package sizes. Personal Trace a discovery
retains the experimental status and unfavorable results of the
[1.3 live evaluation](../reports/product-readiness-1.3.md); this catalogue update
makes no new claim about autonomous research quality.

Open the local reader at **http://127.0.0.1:8767/**. No preview parameter is needed.
