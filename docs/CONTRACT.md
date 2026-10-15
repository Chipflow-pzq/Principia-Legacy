# Data and release contract, schema version 1

Canonical objects are Contribution, Relation, Source, and Review. UTF-8 JSONL stores complete versions. IDs are independent of revisions; content_hash is SHA-256 over canonical JSON excluding content_hash itself. The shared records.py predicate registry defines five layers, directions, and symmetry. schemas/ exports the corresponding external interface. Additional fields permit compatible extensions; changing meanings requires a schema migration.

historical_basis_for is earlier to later. Chronology and citations do not independently establish influence. premise_for with multiple premises means all premises jointly; the viewer displays a diamond relation group. The graph is not globally acyclic. No mixed-layer path is promoted into a transitive proof. Independent formulations remain distinct unless documented evidence establishes identical occurrence identity.

Source anchors identify a retrieved version, page or text-block locator, passage hash, and project-authored evidence summary. They do not redistribute full source text. Page extraction, publication versions, and HTML changes can affect locator reconstruction; raw byte hashes identify the acquired version. Missing or metadata-only access cannot establish checked support. Historical dates record event and precision separately from retrieval/review times.

Machine reviews identify the exact record revision/hash and source-grounded screening request. Human reviews use explicit attestation files; effective review state is derived from exact accepted reviews. Updating a record leaves old approvals attached only to the old version. Unknown contributors/dates stay unknown.

Frozen manifests pin every record revision/hash, dossier checklist, tour, and publication maturity. Canonical old revisions must remain available. SQLite is derived and contains separate snapshot membership. Every response reports release_id. The working snapshot may change; immutable release identifiers cannot be reused with different content.

Correction patches require a reason and matching base hashes. New substantive revisions become candidates. Direct dependents are quarantined for recheck; source changes flag anchored records and their direct relations. Old snapshots remain reproducible. `apply` is an explicit authoring operation, never an HTTP endpoint.

Dossier coverage counts visible screened records against the declared checklist. An initial neighborhood needs at least eight substantive nodes, a resolved endpoint and logged boundary/alternative/attribution inspection outcomes. This says nothing about complete field coverage. Sources consulted in one pass do not establish that all alternatives were searched. Every dossier preserves open ancestry and specific gaps.

The current curation implementation uses bounded explicitly configured source passes. It does not autonomously claim to have completed recursive depth-six historical reconstruction. Candidate source links are a research backlog and may fail or prove irrelevant. Such outcomes remain visible in reports.

Idea families live in a small versioned manifest. They group source occurrences for navigation while retaining distinct contribution IDs, attribution, assumptions and evidence. They do not add graph arrows or establish equivalence, independent discovery, priority or influence. Biology and medicine remain separate dossier tags within their combined pillar.

## Reader navigation extension (1.2)

The four scientific record types remain unchanged. Release manifests also pin
contributor profiles, explicitly verified name aliases and collective-credit
mappings, and additional topic memberships. These are navigation metadata, not
new scientific or historical relationship predicates. Shared membership requires
an exact contribution revision and content hash plus an explanatory reason.
Changed contributions lose these memberships until the interpretation is
rechecked. Correction impact lists include the shared topics. Brief selection and
coverage use the same membership index as the reader.

Contributor pages derive their insight lists from recorded attribution. Collective
credits may resolve to individuals only through an explicit, source-bound author
mapping. Unknown credits stay unknown. Brief research biographies identify their
sources; unsourced biography fields stay empty. Original discovery, exposition,
and collective authorship must not be conflated. A profile is neither a complete
biography nor an independent claim of priority.

`/api/search` returns `results` (ideas), `people`, `topics`, category `totals`,
`offset`, and `limit`. It accepts literal token queries up to 500 characters;
`offset` and `limit` paginate each category. `/api/people` provides a paginated
contributor directory, and `/api/people/{id}` supplies a profile, recorded credits,
linked insight revisions and topics. Contribution inspectors include `topics`
and `people`. All responses retain the release identity and snapshot hash.

Internal `before-*` correction checkpoints remain immutable manifest files. To
avoid duplicating the entire search index for each screened correction, index
these checkpoints only with explicit `build --release CHECKPOINT_ID` restoration.
Published release snapshots remain directly selectable in the reader.

The expanded coverage goal is recorded in `config/coverage_targets.json` and pinned
in new release manifests. Registered topics, populated topics and initial
neighborhoods are reported separately. The minimum planning target is 200
populated topics and 2,000 unique primary-subject insights per subject; additional
reading memberships never inflate unique insight counts. No admission rule is
weakened to meet this target.
