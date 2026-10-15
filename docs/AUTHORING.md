# Authoring and maintenance

Use Python 3.12+ and, for authoring only, `python3 -m pip install -e '.[authoring,test]'`. Run from the project root. The reader needs no installed dependencies. Frontend contributors need a supported Node.js runtime and pnpm; `cd web && pnpm install --frozen-lockfile && pnpm build` rebuilds local assets.

```sh
python3 start.py doctor
python3 start.py validate corpus/
python3 start.py scout --dry-run
python3 start.py curate --dossier M06 --allow-network --env-file /path/to/private.env
python3 start.py build --offline
python3 start.py brief --query "sphere packing" --offline --output build/brief.json
```

The environment file may contain SILICONFLOW_API_KEY. Never commit it. Flash performs routine passage extraction and a separate criticism call. Pro may perform difficult calibration checks. Jobs cache successful results by inputs, model and prompt hashes; failed requests retain redacted receipts. No provider/model fallback occurs. Downloaded documents are untrusted, private cache material. The source candidate register is not accepted evidence.

To propose a correction, prepare JSON with `reason`, `base_hashes` (ID to current hash), and `records` containing complete next revisions. `python3 start.py propose --patch correction.json` writes a reviewable proposed patch. Inspect it, then explicitly run `python3 start.py apply --patch build/proposed-patch.json`. Rebuild the database afterward. Affected records remain out of ordinary browsing until rechecked and admitted in a later explicit revision.

A reviewer-authored attestation contains `reviewer_identity`, `target`, `revision`, `content_hash`, `human_action: true`, `rationale`, and `evidence_checked`. Import it with `review --target ID --revision N --reviewer NAME --attestation-file review.json --scope editorial` (or domain_expert). Do not have a model manufacture the attestation. Rebuild to display effective review status.

Use `impact --target ID --revision N` to inspect dependencies. `refresh --dossier ID --allow-network` acquires a comparison proposal; a detected change never silently updates the corpus. Versioned source changes require ordinary correction patches.

Run `python3 -m pytest -q`, frontend typechecking/build, and the browser checks before `python3 start.py release --id VERSION`. Use a fresh version for changed content; manifests are immutable. Public releases include the complete cross-pillar closure in one compact package. Independent selective domain packs are not implemented in this version.

After applying a correction, recheck its exact evidence before restoring publication:

```sh
python3 start.py review --machine --target NODE_ID --revision 2 --allow-network --env-file /path/to/private.env
```

A supported result creates revision 3 plus an exact-hash **machine** review. Recheck changed contributions first, then their quarantined relations: the relation checker pins and inspects the new endpoint revisions. Unsupported/uncertain outcomes stay unpublished. No human attestation is created. If the exact source byte version is unavailable, this command stops and requires an explicit source update instead of substituting new text.

`scout --dossier C01 --dry-run` inspects the assignment without network access. Add `--allow-network` without `--dry-run` to inspect access/readability of the configured candidate sources. Scouting does not admit claims or establish current frontier importance. Each curation batch prints request and maximum-output-token estimates before it starts; these are ceilings before retries, not a cost prediction. Cached provider calls are keyed by model, prompt and input hashes. Successful source-level admissions are reused on resumption; use the correction/refresh workflow to change an admitted source or claim.

The connection is pinned to a checked public address with normal TLS hostname verification. Redirect destinations are checked again. Source acquisition deliberately ignores environment proxy settings to preserve this boundary; networks requiring a proxy need an explicit, reviewed adapter change. Provider traffic uses its separate fixed API endpoint.

## Bounded expansion

```sh
python3 start.py expand --plan config/plans/foundations-1-1.json --allow-network --env-file /path/to/private.env --workers 4
```

An executed plan's identity and hash are frozen. A plan records each source assignment, explanatory need, parent, depth and explanatory checklist. Depths above six require a recorded reason, with an absolute maximum of ten. The default per-topic allowance is 45 new contributions and survives resumption. A new plan identity records changed research scope. Source assignments never create relationships by themselves.

Admission appends to `corpus/expansions/`. Existing record versions are compared across every corpus file; hash conflicts wait for an explicit revision patch. Resuming a successful pass does not replace its approved evidence. `reports/expansion/` records outcomes, admission decisions and gaps. The legacy `curate` command now uses the same append-only admission boundary.

`scripts/connect_sources.py --env-file /path/to/private.env --batch connections-N --workers 4` proposes and separately checks bounded cross-source connections from exact cached passages. Its inputs contain only admitted current contributions and hash-matching source versions. It preserves joint premises, skips repeated endpoint/predicate connections, and does not fill disconnected components automatically.

`scripts/typeset_notation.py --env-file /path/to/private.env` generates exact-text presentation mappings and a separate notation-equivalence check. This changes rendering, not canonical claim revisions. Run `pnpm --dir web check:math` and browser tests before packaging. Explicit syntax corrections in `config/notation-corrections.json` must state their evidence and remain presentation-only. Substantive mathematical corrections require ordinary record patches.

The expansion review also supports `python3 scripts/editorial_screen.py /path/to/secret.env --baseline 1.0.0-exploratory --output reports/expansion/editorial-1-1.json`. This is significance triage, not a source-fidelity approval. `python3 scripts/check_connections.py --env-file /path/to/secret.env --batch connections-1-1` escalates pinned relationship evidence to the configured explicit Pro model and produces decisions only. Apply exclusions as revision patches; never rewrite accepted versions or label these checks human auditing.

For additional typography, `python3 scripts/typeset_notation.py --env-file /path/to/secret.env --incremental --report reports/notation-next.json` checks only prose without an existing overlay. Run `pnpm --dir web check:math` afterwards; it checks contribution/relationship text, evidence summaries and review rationales.

## Expanded foundations campaign

`config/foundations-curriculum-1-2-v2.json` freezes 1,105 remaining candidate source assignments in 45 bounded batches, after the completed 25-source calibration and removal of nine non-content links. The original campaign and its outcomes remain preserved. `config/active_campaign.json` identifies the active plan. These are research assignments, not accepted insights or completed topics. Only the active batch's topics enter the reader, and unavailable evidence remains a visible gap. Counts are reported against the expanded minimum of 200 populated topics and 2,000 unique primary-subject insights per subject. Neither textbook chapter counts nor shared memberships establish completion.

Inspect the plan without network access:

```sh
python3 scripts/expand_curriculum.py --plan config/foundations-curriculum-1-2-v2.json --max-batches 1
```

Execute or resume the frozen campaign as an authoring operation:

```sh
python3 scripts/expand_curriculum.py --plan config/foundations-curriculum-1-2-v2.json --allow-network --env-file /path/to/private.env --workers 4
```

The runner checkpoints each completed batch, rejects concurrent instances of the same campaign, and refreshes the working database. A Pro editorial pass can withhold generic or redundant fragments through immutable patches; it cannot grant source approval or human review. Exact-revision shared-insight reuse is separately checked against the new source. A bounded second lookup uses extracted claims, rather than a broad chapter title, to find closer reuse candidates. At most one optional extraction refinement follows; similarity alone never merges records. Failed sources, duplicate/reuse decisions, usage receipts and gaps remain inspectable. Provider work stops for inspection after excessive source failures, a large increase in unknown-charge attempts, or the conservative known-token planning subtotal trigger (default CNY 1,000). This is not exact billing enforcement of the owner-managed US$300-equivalent allowance.

Create `.work/foundations-curriculum-1-2-v2.stop` to stop between batches; remove that file before explicitly resuming. `reports/campaigns/foundations-curriculum-1-2-v2.json` records progress, and `BUILD_STATUS.md` records actual admitted coverage. `--max-batches N` means the first N batches of the plan, including already completed batches, rather than N additional batches. Published release manifests remain unchanged. Select **working** in the reader, then reload, to see a newly completed batch. Typography checks, release-wide verification and a new release freeze are separate finishing steps.

Contributor biographies in `manifests/people.json` require sources. Only explicit aliases join names. `credit_groups.json` can expand a collective byline into named people only for specified source identities; it preserves the original credit role. `topic_memberships.json` adds explanatory reading routes pinned to a contribution revision/hash and, for machine-screened reuse, source anchors and screening receipts. A changed contribution or supporting source invalidates that route until it is checked again. These navigation manifests never create historical arrows.
