# Development

The reader has no Python runtime dependencies. Node.js is needed only to rebuild the interface; model-provider credentials are needed only for explicitly invoked authoring operations.

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
python start.py build --release 1.2.0-exploratory --offline
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

See [AUTHORING.md](AUTHORING.md) for source acquisition and paid model use. Reading, testing and index rebuilding must never trigger a provider call. Follow [PUBLISHING.md](PUBLISHING.md) to prepare a source archive; do not publish caches, credentials or working databases.
