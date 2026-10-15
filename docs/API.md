# Read-only API

All routes use GET (or HEAD) on the loopback reader. Successful JSON responses include `release_id` and `snapshot_hash`; records include stable `id`, `revision` and `content_hash`. Pass `release=<immutable-id>` to select a snapshot. Unknown snapshots return 400. Inspectors return every pinned source version and revision-specific reviews. There are no HTTP write, authoring, model or file-upload routes.

| Route | Parameters and result |
|---|---|
| `/api/info` | Pillars, counts, predicate registry, tours, snapshot choices and review summary |
| `/api/search` | `q`, `pillar`, `human=true`, `limit` (maximum 100), `offset`; literal FTS terms; separate idea, person and topic results with per-category totals |
| `/api/contributions/{id}` | Contribution, source details, exact-revision reviews, all indexed topic memberships and credited people |
| `/api/people` | `q`, `limit` ≤100, `offset`, `human=true`; scientist and contributor directory |
| `/api/people/{id}` | Sourced profile or explicitly incomplete attribution page, related ideas with credit notes, and topics; optional `human=true` |
| `/api/relations/{id}` | Predicate, scope, warrant, joint premises, source details and reviews |
| `/api/neighborhood` | `dossier` or `seed`, `layers` comma-separated (`none` for empty), `human=true`, `limit` ≤200, `hops` ≤6, `direction=both/ancestors/descendants` |
| `/api/dossiers` | All registered topic assignments, including empty ones, current coverage, checklist evidence and gaps |
| `/api/changes` | `from`, `release` (destination snapshot); added, removed and changed record identities between snapshots |
| `/api/brief` | `q`, optional `dossier`; deterministic evidence package, action scope `read_only` |

Topic responses also report `available_count` after the review filter and prioritize the topic endpoint. Increasing `limit` retains the existing topic node set. The reader starts with at most 40 ideas and expands to at most 200.

Person profiles and additional topic memberships are snapshot-pinned navigation metadata, not a fifth scientific record type. A shared membership pins the exact contribution revision and hash; a changed contribution requires a fresh membership decision. Source-bound collective author credits do not merge independent discoveries. Profile biographies identify their own sources separately from an insight's evidence. Membership is not an inferred historical relationship.

The neighborhood cap is a response bound, not an assertion of complete ancestry. A relation is included only when all its premises and conclusion fit the returned graph. Traversal direction respects the registry, including symmetric predicates. Mixed-layer paths do not imply a transitive proof. Candidate/quarantined records never appear in normal search or graph responses.

The CLI supports explicit local policy-profile input to briefs. Policy text is data and never changes the fixed read-only action scope. Brief exports preserve every selected endpoint and referenced source revision across pillars. Full releases contain all canonical records; selective subject archives are not provided in this release.

The server rejects unexpected Host headers and all write methods, parameterizes SQL, restricts file serving to `web_dist`, uses a local-only Content Security Policy, and does not make outbound requests. Use the CLI for patches and review attestations.
