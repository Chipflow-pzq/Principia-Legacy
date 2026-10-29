# Remote authoring and offline review

The canonical dataset lives in one private data home. SQLite is a rebuildable reader index; it is never the source of scientific truth. Code and data may be updated independently, but a reader always identifies the exact snapshot it serves.

## Private layout

The current 1.5 development installation uses `/data/xia/Principia-legacy/staging/1.5/` on the `principia-hk` SSH host:

| Directory | Purpose |
|---|---|
| `code/` | This branch's Python code, scripts and prebuilt reader |
| `data/corpus/`, `data/manifests/` | Canonical record revisions and immutable releases |
| `data/.work/` | Private source archives, resumable jobs, receipts and commit journal |
| `data/build/` | Rebuildable SQLite and derived reports |
| `backups/` | Checksummed backups and explicit review exports |
| `authoring-venv/` | Optional acquisition, PDF parsing and authoring dependencies |

Credentials remain in an external file readable only by its owner. Neither the public reader nor a release archive includes that file. The staging parent is private, the development reader binds to loopback, and the public reverse proxy has no staging route. The existing public deployment remains separate.

## Run a bounded campaign

Freeze source assignments, explanatory needs and topic checklists before a batch. Run from `code/`, using the authoring environment:

```sh
../authoring-venv/bin/python scripts/run_campaign.py \
  --data-home ../data --env-file /private/path/authoring.env \
  foundations-1-5-001.json
```

Only use an already reviewed plan filename. Four provider requests may run concurrently; source admission and corrections use one writer lock and an idempotent commit journal. Compilation captures a consistent snapshot under that lock, builds separately, then atomically replaces the query index. A later queued build includes admissions made during compilation.

Provider receipts preserve exact model IDs, prompt/input hashes, attempt outcomes, token counts and uncertain charges. A timed-out request is never assumed free. An uncertain submission is not automatically replayed. Inspect the original receipt before explicitly deciding to retry; failed source downloads and failed model requests are different cases. The budget configuration provides conservative pause thresholds, not a provider billing guarantee.

If a process or SSH session is interrupted, reconnect and inspect its process, log and job receipts before restarting. Completed jobs are reusable only for the same hashed input. Pending commit-journal entries recover under the writer lock. Never edit an immutable release to make a failed job disappear.

## Lightweight preview through SSH

The private reader runs as `principia-legacy-staging15.service`, listening only on
`127.0.0.1:18765`. Its unit is in `hosting/principia-legacy-staging15.service`.
The public `principia.service` uses a separate read-only data home and runtime; staging updates never activate it. See [public deployment](DEPLOYMENT-1.5.md).

On the Mac, from the source tree or the small preview package:

```sh
python3 start-cloud.py
```

Open `http://127.0.0.1:8767/`. The launcher opens a private SSH forward using the
already configured `principia-hk` host and trusted host key. It serves only bundled
assets locally and forwards read-only API calls. It copies no credentials,
scientific data or model to the client. A single SSH supervisor reconnects after network interruptions with bounded
backoff; pending read-only requests resume automatically. A manual session stops
with Ctrl-C. Use an explicit offline snapshot for reading without connectivity.

Personal exploration still runs in the browser: research prompts, keys and
generated maps are not uploaded to the atlas server. Ordinary atlas search terms
are sent to its read-only search API. Neither reader logs those queries.

Build a new small distribution without overwriting an existing preview:

```sh
python3 scripts/package_cloud.py /path/to/new-preview
```

### Mac login startup

The user's Mac runs `net.chipflow.principia-legacy.preview` as a per-user LaunchAgent.
It starts the thin reader at login and restarts it if it exits. This installs no
credentials or new remote access; the same trusted SSH alias is used. To install
or update it on another authorized Mac, using Python 3.12+:

```sh
python3 scripts/install_cloud_login.py /absolute/path/to/Principia-Legacy-Preview
```

The installer prints the stop/remove command. The plist lives in the user's
`~/Library/LaunchAgents/`; logs are in `~/Library/Logs/Principia-Legacy/`.
The reader binds only to loopback. `/api/connection` exposes its connection state,
not credentials, process IDs or private queries. Browsing retries only atlas GET
requests: model generations and paid provider calls never use this recovery path.

### Optional semantic index

The authoring environment and any reader configured for semantic retrieval need `requirements-semantic.txt`; ordinary offline readers do not.
The accepted runtime is FastEmbed 0.7.4 with the CPU ONNX encoder
`sentence-transformers/all-MiniLM-L6-v2`. It adds no database daemon or paid inference
API. The model cache is approximately 87 MB; the review4 derived index is 14.2 MB.
SQLite remains the keyword and scientific-record index.

Build once on the server from the exact frozen snapshot:

```sh
../authoring-venv/bin/pip install -r requirements-semantic.txt
../authoring-venv/bin/python scripts/build_semantic_index.py \
  --data-home ../data --model-cache ../models \
  --output ../data/build/semantic-NEW-SNAPSHOT
```

The first authoring build downloads the configured encoder. Later reader startup
uses `HF_HUB_OFFLINE=1` and `local_files_only=True`; model/index checksums and the
snapshot hash must match. Set `PRINCIPIA_SEMANTIC_HOME` to the completed index and
`PRINCIPIA_MODEL_CACHE` to the cache, then restart the private service. A new
scientific snapshot requires a new index; never repoint an existing manifest to
changed vectors. Preserve the index manifest with release verification reports.

Canonical backups remain sufficient to rebuild SQLite. The encoder and index are
derived assets; retain a checksummed copy of `models/` separately if restoration
must work without downloading the encoder. The service has read-only paths and a
1 GB memory limit. Inspect service status and test retrieval after activation.

## Back up, restore, then verify

```sh
python3 start.py --data-home ../data backup --output ../backups/private.tar.gz
python3 start.py restore --archive ../backups/private.tar.gz \
  --destination ../restored --sha256 RECORDED_SHA256
python3 start.py --data-home ../restored validate
python3 start.py --data-home ../restored build --offline
```

Restore always requires a new destination. Checksums, inventory, member paths and archive types are checked before activation. Private backups include source evidence and receipts; restrict their access. A backup on the same server protects against application mistakes but does not protect against losing the server. Keep an independently verified off-host copy under an appropriate retention policy.

For a review export, first freeze a named release, then exclude all private authoring caches:

```sh
python3 start.py --data-home ../data snapshot \
  --release RELEASE_ID --output ../backups/review.tar.gz
```

Download the archive and its receipt, verify the SHA-256, restore into a new local data home, and rebuild with the matching code. Review exports retain canonical revisions and historical manifests; they do not contain acquisition caches, provider jobs or credentials. They are deliberately downloaded copies, not a second authoring authority. Record the source snapshot and checksum in every local acceptance report.

Public activation, its rollback target and GitHub publication are separate release decisions. Private staging does not change the deployed public snapshot.

Internal `before-*`, numbered `-qaN`, and numbered `-reviewN` snapshots are retained in canonical storage. Only an explicitly selected internal snapshot is indexed by default alongside public releases. This prevents repeated development builds from multiplying reader indexes; `build --release <id>` restores one exactly.
