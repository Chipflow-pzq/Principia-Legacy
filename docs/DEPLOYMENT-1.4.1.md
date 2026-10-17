# Publication of 1.4.1

The owner accepted the local reader and authorized deployment and a GitHub pull
request on 17 October 2026. Reader **1.4.1** uses the unchanged, immutable
**1.4.1-exploratory** scientific snapshot. Source changes are proposed through
`codex/release-1.4.1`; the maintainer merges the pull request.

## Installation design

The public entry is [atlas.chipflow.net/web/legacy/](https://atlas.chipflow.net/web/legacy/).
The application stays under `/data/xia/Principia-legacy/`:

```text
repository.git/             Git history transferred without credentials
releases/RELEASE_ID/         exact source checkout, compiled database, hosted assets
current -> releases/…       active release
deployment/RELEASE_ID/      checksums, configuration backups, activation receipt
.venv/                      existing pinned Gunicorn runtime
```

The previous flat 1.2 installation is retained. The Legacy service remains
`principia.service`, running as the unprivileged `principia` account on
`127.0.0.1:8766`. Nginx exposes only its hosted assets and read-only API.
Its HTML policy permits the browser's explicit personal-exploration requests;
other applications' routing and policies remain independent.

## Verification and rollback

Before activation, verify the Git bundle, every supplied artifact checksum,
SQLite integrity, and a separate loopback canary under the runtime account.
Save the exact active service unit and Legacy Nginx snippet. Validate Nginx
before reloading, then check the public release, search, work and person pages,
graph interaction, deep links, privacy boundaries and neighboring site health.

For this migration, rollback restores the saved service unit and Legacy snippet,
runs `systemctl daemon-reload` and `nginx -t`, then restarts only
`principia.service` and reloads Nginx. The old code and database remain at their
original paths. For later upgrades, use a new release directory and retain the
previous `current` target and configuration. Never synchronize over an active
release or copy private keys to the server.

The activation results and exact commit/checksums will be appended after public
verification. Earlier local acceptance evidence is in
[the readiness report](../reports/product-readiness-1.4.md); it is not a
production load test or a qualified human audit.
