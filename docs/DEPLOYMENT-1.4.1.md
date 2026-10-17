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

## Activated and verified

Activated **17 October 2026 at 07:50 UTC** (15:50 Asia/Shanghai).

| Item | Value |
|---|---|
| Active release directory | `/data/xia/Principia-legacy/releases/20261017073758Z-1.4.1-r2` |
| Deployed source commit | `2c2fcf1442424b5bd2f2c03dd770366babcec414` |
| Server Git tag | `deployed/20261017073758Z-1.4.1-r2` |
| Operational evidence and backups | `/data/xia/Principia-legacy/deployment/20261017073758Z-1.4.1-r2/` |
| Pull request | [#1](https://github.com/Chipflow-pzq/Principia-Legacy/pull/1), intentionally unmerged |

All 64 runtime files were checksum-verified. The database is byte-identical to the
owner-accepted offline package. Local publication checks passed 117 backend tests,
TypeScript, both frontend builds, desktop/mobile hosted-prefix tests, and an
offline smoke test with zero external socket attempts. GitHub CI separately passed
on Linux, macOS and Windows for the accepted source commit; later documentation
commits have their own check results on the PR.

The private backend canary verified spelling recovery, works, people, a graph,
historical snapshots and read-only boundaries. Actual Nginx checks verified the
HTML, hashed JavaScript/CSS, a single appropriate HTML security policy, and denied
private paths and writes. Public HTTPS also verified the live snapshot and record
APIs from outside the server. The main website remained healthy; its service PID
and unrelated configuration files were unchanged. No provider request or paid
exploration was initiated.

The first activation exposed a trailing-slash file-alias error in Nginx. It was
rolled back, corrected, and covered by `hosting/scripts/check_public.py` before the
successful second activation. Both attempts and the temporary canary configuration
failure are retained in the operational record.

The browser-control tool subsequently timed out, so a completed interactive
public-site walkthrough is **not claimed**. Desktop/mobile interaction was checked
against the exact hosted build locally; final public HTML, assets and APIs passed
over HTTPS. These checks are not a production load test or a qualified human audit.
See the [deployment receipt](../reports/deployment-1.4.1.json) and
[earlier acceptance evidence](../reports/product-readiness-1.4.md).
