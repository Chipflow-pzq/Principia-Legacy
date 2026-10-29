# Development

The reader has no Python runtime dependencies. Node.js is needed only to rebuild the interface. Credentials are needed for explicitly invoked authoring or optional personal exploration; ordinary reading needs none.

## Repository map

| Path | Responsibility |
|---|---|
| `src/principia_legacy/` | Records, SQLite indexes, graph queries, corrections, curation, releases, CLI and local serving |
| `web/src/` | React/TypeScript reader, one Cytoscape renderer, local KaTeX |
| `web_dist/` | Prebuilt offline interface, committed for installation-free reading |
| `hosting/` | Optional read-only WSGI adapter, configuration examples and tests |
| `corpus/`, `manifests/`, `schemas/` | Immutable JSONL versions, snapshot membership, navigation and schema/predicate contracts |
| `config/`, `prompts/`, `tours/` | Explicit curation plans, model contracts and reading journeys |
| `tests/`, `scripts/` | Integrity/security tests, frozen research fixtures and maintenance utilities |
| `docs/`, `reports/` | Guides, source provenance, dated evidence and limitations |
| `build/`, `.work/`, `dist/` | Ignored generated database, private authoring work and release artifacts |

## Python

Use Python 3.12 or later. Optional dependencies belong in a local virtual environment:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[authoring,test]'
python -m pytest -q
python start.py validate
python start.py build --release 1.4.1-exploratory --offline
python start.py doctor
```

On Windows, activate with `.venv\Scripts\activate`. The full Python suite includes hosting access-boundary tests; it does not require a live server or API credentials. A test fixture builds the frozen index if absent.

## Frontend

Use Node.js 24+ and pnpm. Dependencies are pinned in `web/pnpm-lock.yaml`.

```sh
pnpm --dir web install --frozen-lockfile
pnpm --dir web build
python3 start.py serve --offline
```

For development, run `pnpm --dir web dev` in a second terminal. Vite forwards `/api` to the local reader on port 8765. The API client derives its prefix from Vite's base URL, so local and hosted builds share the same source.

The hosted build uses `/web/legacy/` by default:

```sh
pnpm --dir web build:hosted
```

For a different mount point, run `pnpm --dir web exec vite build --mode hosted --base /atlas/ --outDir ../web_hosted`. The generated `web_hosted/` directory is ignored. Serve it with matching reverse-proxy routing; see [Hosting](../hosting/README.md). No compiled-JavaScript patching is needed.

## Verification

With a local reader running and Google Chrome installed:

```sh
pnpm --dir web test
pnpm --dir web check:math
python scripts/acceptance.py
python -S scripts/offline_smoke.py .
python scripts/check_living.py
```

Set `PRINCIPIA_TEST_URL=http://127.0.0.1:18765` to test a reader on another port. The browser suite includes desktop and emulated-mobile workflows. Performance collection uses Unix `ps` and `lsof`; Windows backend tests are supported, but that particular memory measurement needs a Unix host. Never run browser tests against the public site: they belong on an isolated local reader.

After building both the database and hosted assets, verify the hosted mount with `pnpm --dir web exec playwright test --config playwright.hosted.config.ts`. This starts a disposable, loopback-only preview on port 18766 and checks the actual adapter and hosted assets on desktop and mobile. It leaves production configuration untouched.

## Maintain the contract

Read [CONTRACT.md](CONTRACT.md) before changing meanings or record semantics. Stable identities, revision hashes, source anchors and historical snapshots must remain reproducible. Corrections use new revisions and explicit patches. Preserve independent formulations and distinguish navigation memberships from evidenced relationships.

See [AUTHORING.md](AUTHORING.md) for canonical curation and [PERSONAL_EXPLORATION.md](PERSONAL_EXPLORATION.md) for the separate browser agent. Ordinary reading, automated fixture tests and index rebuilding never trigger a provider call. Live provider checks are explicit, paid authoring QA and must use an external secret with no recording of headers or keys. Follow [PUBLISHING.md](PUBLISHING.md) to prepare a source archive; do not publish caches, credentials or working databases.


## Opt-in live browser acceptance

The ordinary browser suite uses synthetic fixtures and does not spend API credit.
For the six user-supplied exploration cases, `scripts/live_browser_qa.mjs` operates
the actual browser form, discovers the account’s exact model IDs, downloads each
map, and checks its inspectors. This **submits paid provider requests**. Run from
the repository root with the development dependencies installed:

```sh
SILICONFLOW_ENV_FILE=/absolute/path/to/external.env \
PRINCIPIA_TEST_URL=http://127.0.0.1:8767 \
node scripts/live_browser_qa.mjs deepseek-ai/DeepSeek-V4.1-Flash
```

Pass additional exact model IDs as additional arguments to repeat all six cases.
The credential file is read by the test process; it is never copied into the repo.
The browser sends the key directly to SiliconFlow, with persistence unchecked.
Outputs, source passages and diagnostic responses stay in ignored
`.work/live-browser/<timestamp>/`. A nonempty `STOP` file there stops the runner
after the current case. Reports retain failures, timings, receipts and source
hosts. Structural thresholds are diagnostics, not scientific correctness scores;
inspect the actual claims and arrows before accepting a result.

A stopped run can continue without paying to repeat completed cases:

```sh
SILICONFLOW_ENV_FILE=/absolute/path/to/external.env \
PRINCIPIA_TEST_URL=http://127.0.0.1:8767 \
PRINCIPIA_QA_RESUME_DIR=.work/live-browser/RECORDED-RUN-DIRECTORY \
node scripts/live_browser_qa.mjs deepseek-ai/DeepSeek-V4.1-Flash
```

Remove the run's `STOP` file before resuming. The runner checks the original URL,
model, query protocol and application bundle; it does not replay completed failures
or silently resubmit an unfinished, potentially charged attempt. Resume only on
the same build. Keep all earlier outcomes when reporting an iteration.

## Work catalogue and offline search

`works.py` validates work identity, exact evidence-pinned memberships and scoped
projections of checked insight connections. `retrieval.py` owns bounded spelling
and related-concept expansion; it has no external service or embedding dependency.
`compiler.py` builds SQLite indexes; `query_index.py` builds compact membership,
coverage and catalogue indexes. `queries.py` owns bounded catalogue/search pages,
`graph_queries.py` owns graph traversal, and `storage.py` retains the reader facade
and revision-aware inspectors. `Works.tsx` renders work navigation.
The source selection is in small configuration manifests; the deterministic
`scripts/build_work_catalog.py` compiles it without calling a provider.

Homepage summaries and collection pages use precomputed SQL indexes. Individual
topic, work and person memberships have independent pagination; the graph's
200-node limit does not hide the remaining list entries. Snapshot metadata uses
compressed payloads in SQLite, without altering canonical manifest hashes. FTS
indexes each unique insight revision once and joins snapshot membership at query
time. No ORM, embedding service or server-side personal-query cache is required.

Personal research downloads hash-checked public search shards, pins their snapshot,
and ranks compact entries in a Web Worker. Full evidence records are fetched only
for bounded matches. The public-shard cache and saved-map metadata index are separate
from personal map contents. See [remote authoring and offline review](STAGING.md).

Synthetic scale fixtures must remain outside `corpus/`. `scripts/scale_reader.py`
measures 10k–100k generated insight indexes; `scripts/scale_browser.mjs` measures the
actual browser ranking worker with synthetic entries. Report broad and distinct
queries, compilation memory, reader memory, browser memory and network latency
separately. A passing average cannot hide a failing tail-latency target.
