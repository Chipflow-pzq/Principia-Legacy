# Principia-Legacy 1.5 · exploratory release

This upgrade deepens the atlas and makes a larger collection practical to browse. The owner accepted `1.5.0-review5` on 29 October 2026. Its scientific records are promoted unchanged to `1.5.0-exploratory`; all seven earlier public snapshots are retained. The [dated acceptance report](../reports/coverage-review5-20261028.md) separates software checks, scientific coverage, model screening, spending, and human review.

## Follow an explanation without losing your place

Topics, works, insights, and individual contributors remain one connected reading experience. Collections now page independently; the graph retains its 200-node bound while every topic insight remains reachable in the list. Subject, coverage, connection settings and collection positions survive navigation and reload. Returning from a detail restores the earlier view, scroll and keyboard focus. The insight inspector leads with the claim before offering related works and topics.

A new **Reading route checked by AI** filter distinguishes a coherent, revision-pinned explanatory route from a topic that merely contains records. This is machine editorial assessment. It does not establish historical influence or qualified human review.

## Deeper content, with visible boundaries

The campaign recovers unpublished candidates, adds sourced foundations and engineering explanations, checks cross-work connections independently, and withholds weak arrows and non-substantive fragments. Corrections retain their earlier revisions and invalidate dependent interpretations. Independent formulations and modern expositions keep distinct attribution.

Catalogue breadth, topics containing insights, and ready reading routes are counted separately. The intended milestone is 100 supported topics and 1,000 substantive insights in each subject; the actual shortfall appears in [BUILD_STATUS](../BUILD_STATUS.md). Numerical growth does not certify scientific quality. No qualified human audit has been performed.

## A small architecture that can grow

SQLite and FTS5 remain the query engine. Indexed filtering, bounded record reads, compact summaries and shared historical indexes replace repeated whole-collection work. Personal exploration ranks compressed, snapshot-pinned public search shards in a browser worker and fetches only bounded record matches. Its private research prompt is not sent to the atlas server.

Canonical authoring now resides in private server staging, with four-request coordination, a single admission writer, an idempotent journal, immutable releases and tested backup restoration. The Mac uses a small cloud reader; offline snapshots are downloaded only when explicitly requested. [Operations and recovery](STAGING.md).

## What remains experimental

Trace a discovery still depends on source availability and the selected provider. Live browser evaluations preserve throttling, delayed responses, rejected arrows and incomplete maps. Progress, pause/resume and usage receipts help explain these outcomes; they do not guarantee a complete map or a fixed completion time. [Personal exploration](PERSONAL_EXPLORATION.md).

The earlier development campaign recorded performance limits at 100,000 synthetic insights. Synthetic fixtures are kept outside the scientific corpus. Earlier research-pilot findings remain unchanged and do not establish an alignment benefit.

## Code and data editions

The public reader uses an isolated, read-only database compiled from the accepted server corpus. The source PR includes the complete 1.5 software and retains the existing 1.4.1 reference corpus so `python3 start.py` remains runnable offline. The expanded corpus, large query index, model, source archives and provider receipts remain on the server.

[Deployment and rollback](DEPLOYMENT-1.5.md) · [Local preview](LOCAL_PREVIEW.md) · [Installation](../README.md#run-locally) · [Publishing](PUBLISHING.md).
