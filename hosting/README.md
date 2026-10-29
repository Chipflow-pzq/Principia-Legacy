# Optional public hosting

The live example is **https://atlas.chipflow.net/web/legacy/**. Reader 1.5 publishes the accepted `1.5.0-exploratory` snapshot. See the [deployment record](../docs/DEPLOYMENT-1.5.md) for the verified public installation. The adapter exposes only explicitly allowed immutable snapshots, never the mutable working atlas or authoring operations.

The local reader remains a Python-standard-library application. Public hosting adds a small WSGI adapter, Gunicorn and a reverse proxy. The production adapter also supports a separately managed data home and an optional offline semantic index. Server accounts, keys, operational backups and private configuration are deliberately outside this repository.

## Build a standalone hosted reader

Start from this complete source tree in a dedicated application directory. Use Python 3.12+ and Node.js 24+ with pnpm for the build:

```sh
python3 start.py build --release 1.4.1-exploratory --offline
pnpm --dir web install --frozen-lockfile
pnpm --dir web build:hosted
cp hosting/hosting.example.json hosting.json
```

The command above uses the reference corpus bundled with Git. The full public data edition is maintained separately.

Edit the `hosts` list in `hosting.json` to contain your exact public hostname. Keep only explicitly published releases in `public_releases`. The default configuration permits local hostnames only; it does not authorize a production deployment.

Install the optional server in a dedicated virtual environment:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --require-hashes -r hosting/requirements.txt
export PRINCIPIA_BUNDLE="$PWD"
cd hosting
gunicorn --config gunicorn.conf.py 'app:create_app()'
```

Gunicorn listens on **127.0.0.1:8766**. A local health check with the example configuration is:

```sh
curl --fail -H 'Host: localhost' http://127.0.0.1:8766/healthz
```

Builds use `/web/legacy/` as the frontend mount point. Vite's `--base` controls both asset and API URLs; the API client requires no manual editing of compiled JavaScript. A hosted build displays **Public · read-only**, while the local build displays **Local · offline ready**.

## Reverse proxy

Use `config/nginx-legacy.conf.example` as a **location-level example inside your own HTTPS server block**. Adapt its application paths, allowed hostname and mount prefix, and define the commented rate-limit zones at Nginx `http` scope. Keep TLS setup and existing routes under the operator's control. Do not replace a shared host's configuration wholesale.

The proxy serves only `web_hosted/` assets and forwards `/web/legacy/api/` and `/web/legacy/healthz` after removing the mount prefix. Keep SQLite, canonical files, manifests, caches and `hosting.json` outside the public document root. Use a dedicated unprivileged runtime user; build the database before starting a read-only service. The systemd example uses `/opt/principia-legacy` and must be adapted before installation.

The adapter checks allowed hosts, permits GET/HEAD only, bounds queries and cache memory, opens SQLite read-only, and denies unpublished snapshots. It has no source-download, provider-call or authoring endpoints. These boundaries do not replace operator-managed TLS, rate limits, patching and access control.

Personal exploration runs in the browser. When deploying, its HTML Content-Security-Policy must allow `connect-src 'self' https://api.siliconflow.cn https://api.crossref.org https://www.ebi.ac.uk https://en.wikipedia.org`. The example scopes this policy to the app entry page. Check inherited headers: multiple CSP headers intersect, so an additional `connect-src 'self'` policy would still block exploration. In Nginx, location-level `add_header` directives replace inherited header directives; preserve any required HSTS or other site headers explicitly when adapting the example. No server proxy, server key, write endpoint or user-result directory is required. Ordinary reading remains offline. Browsers send personal questions to external services only when readers explicitly start an exploration.

## Prepare a minimal bundle from an offline release

If you already have a verified offline release ZIP, extract only its required reader files:

```sh
python3 hosting/scripts/prepare_bundle.py \
  dist/principia-legacy-1.4.1-exploratory.zip \
  /path/to/new-reader-bundle --host atlas.example.org
```

The script verifies archive and per-file checksums, refuses an existing destination, and emits `hosting.json` plus a checksum receipt. Repeat `--host` for additional allowed hostnames. Copy the hosting adapter and the matching `web_hosted/` build alongside that bundle before starting it. It does not transfer files, install services or change a running site.

## Verification and updates

Run `python -m pytest -q hosting/tests` from the repository root. Tests use a disposable configuration and the frozen database; no production credentials are needed. For an existing bundle, set `TEST_BUNDLE=/path/to/bundle`.

For each deployment, use a new immutable directory, validate the selected snapshot and frontend prefix, retain the prior bundle for rollback, then verify search, a topic, an insight, a scientist profile and `/healthz`. Deployment and certificate issuance are separate operator actions. The checked-in examples are templates, not copies of private server configuration. Consult the deployment record for the active layout.

## Separate production data and semantic retrieval

Set `data_home` in the operator-owned `hosting.json` to an absolute data directory containing `build/atlas.sqlite`. Omit it to use the bundle itself. HTTP requests cannot change this path. Keep it outside `web_hosted/`, owned by the operator and readable, but not writable, by the service account.

Compile the database with the matching 1.5 software in an isolated build directory. Do not reuse an older schema in place or point production at mutable authoring staging. Keep every formerly public manifest byte-for-byte unchanged. Promoting an accepted candidate uses the explicit frozen manifest:

```sh
python3 start.py --data-home /private/authoring-data promote \
  --from 1.5.0-review5 --id 1.5.0-exploratory
```

This changes only the release identity and does not activate a reader. Build an index containing only the approved public snapshots, validate it, then configure the default and allowlist. Retain the old code, data and runtime for rollback.

Semantic search is optional and server-side. Install `requirements-semantic.txt` in the hosting runtime; on the deployed Linux x86_64 platform the complete tested dependency set is pinned in `requirements-linux-1.5.txt`. Prebuild the index with `scripts/build_semantic_index.py` from the exact public snapshot. Set `PRINCIPIA_SEMANTIC_HOME`, `PRINCIPIA_MODEL_CACHE` and `HF_HUB_OFFLINE=1` in the service environment. The adapter refuses startup for a configured index that fails its snapshot or checksum checks. Startup and search do not download a model; normal reader requests have no provider dependency. Limit numerical library threads on small servers.

Test the new release on a separate loopback listener before atomically switching the code symlink and restarting the service. Verify the HTTPS mount, historical links, semantic searches and neighbouring applications afterward. Retain a dated receipt of database, assets, runtime and source hashes.
