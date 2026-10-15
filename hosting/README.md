# Optional public hosting

The live example is **https://atlas.chipflow.net/web/legacy/**. The public service serves the immutable `1.2.0-exploratory` snapshot. It does not expose the mutable working atlas or authoring operations.

The local reader remains a Python-standard-library application. Public hosting adds a small WSGI adapter, Gunicorn and a reverse proxy. `app.py` and `gunicorn.conf.py` were reconciled with the deployed adapter on 15 October 2026. Server accounts, keys, operational backups and private configuration are deliberately outside this repository.

## Build a standalone hosted reader

Start from this complete source tree in a dedicated application directory. Use Python 3.12+ and Node.js 24+ with pnpm for the build:

```sh
python3 start.py build --release 1.2.0-exploratory --offline
pnpm --dir web install --frozen-lockfile
pnpm --dir web build:hosted
cp hosting/hosting.example.json hosting.json
```

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

## Prepare a minimal bundle from an offline release

If you already have a verified offline release ZIP, extract only its required reader files:

```sh
python3 hosting/scripts/prepare_bundle.py \
  dist/principia-legacy-1.2.0-exploratory.zip \
  /path/to/new-reader-bundle --host atlas.example.org
```

The script verifies archive and per-file checksums, refuses an existing destination, and emits `hosting.json` plus a checksum receipt. Repeat `--host` for additional allowed hostnames. Copy the hosting adapter and the matching `web_hosted/` build alongside that bundle before starting it. It does not transfer files, install services or change a running site.

## Verification and updates

Run `python -m pytest -q hosting/tests` from the repository root. Tests use a disposable configuration and the frozen database; no production credentials are needed. For an existing bundle, set `TEST_BUNDLE=/path/to/bundle`.

For each deployment, use a new immutable directory, validate the selected snapshot and frontend prefix, retain the prior bundle for rollback, then verify search, a topic, an insight, a scientist profile and `/healthz`. Deployment and certificate issuance are separate operator actions. The examples in this repository were prepared locally; they have not replaced the currently running site's configuration.
