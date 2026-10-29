# Data and release contract, schema version 1

## Optional cloud retrieval extension (1.5)

The read-only search API retains keyword, curated-alias and spelling matching as
its first pass. Expanded multiword concepts use phrase matching; scattered words
do not establish a scientific synonym. Only an empty result can invoke optional
semantic retrieval, followed by explicitly declared related-concept suggestions.
Suggestions preserve all four entity categories, subject/review filters, revision
pins and pagination. `search_interpretation.match_mode` identifies `direct`,
`semantic` or `related`; semantic similarity never admits a claim or relationship.

The optional server index pins the exact snapshot, encoder identity and file
hashes. It is a rebuildable normalized vector matrix with bounded results, not a
second canonical dataset. The reader loads the cached encoder offline; it never
downloads a model or submits queries to an inference provider. A missing or
mismatched index leaves keyword search available. Ordinary browsing queries go
to the private read-only server and are not logged by the reader. Personal
exploration prompts, keys and maps retain their separate browser-local boundary.

The thin local launcher serves bundled assets and forwards only GET API reads to
a fixed loopback SSH tunnel. User headers, credentials and cookies are not
forwarded; redirects and oversized/non-JSON responses are rejected. It requires
network access, downloads no scientific dataset, and does not silently substitute
an older local database after a connection failure. Offline packages remain a
separate, explicit distribution option.

## Canonical records

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
Published release snapshots remain addressable through pinned links and release comparisons. The sidebar has no release selector.

`/api/changes` accepts optional `limit` (capped at 200) and `offset` parameters.
Paginated responses return contribution/relation references in deterministic ID
order, with a separate page for each of `added`, `removed`, and `changed`.
`totals` counts those references before pagination; `record_counts` also counts
source and review changes. Revision and snapshot pins are preserved. Omitting
`limit` retains the original complete response for export clients. The browser
requests 20 entries per category and cancels obsolete comparisons.

The expanded coverage goal is recorded in `config/coverage_targets.json` and pinned
in new release manifests. Registered topics, populated topics and initial
neighborhoods are reported separately. The minimum planning target is 200
populated topics and 2,000 unique primary-subject insights per subject; additional
reading memberships never inflate unique insight counts. No admission rule is
weakened to meet this target.

## Personal exploration boundary (1.3 preview)

Personal maps use a separate `principia-exploration/v1` format. They are never
canonical records or release members. Their status is always `unverified_draft`
and their action scope is always `read_only`, including on import. Neither a
successful quotation match nor a second model critique establishes scientific
correctness, priority, human review or publication approval.

The browser runs retrieval and generation directly. The server exposes only a
paginated public `/api/exploration-index`, capped at 200 revision-pinned entries;
it accepts no exploration uploads or credential/model requests. Matching a user's
question against that index happens on their device. Explicit IndexedDB saving
and portable JSON export retain only a validated map, citations and nonsecret
request receipts. Keys remain in memory unless the user explicitly enables local
credential storage in global Settings. Remembered keys are scoped to this browser
profile and origin; they never enter map files, requests to the atlas server or
release artifacts. Clearing the key removes it from the current tab and saved
settings. Source instructions grant no authority.

The live predicate registry governs layer, direction and symmetry. Joint premises
stay grouped; unsupported quotations, metadata-only evidence, invalid endpoints,
reverse-dated historical bases and duplicate symmetric connections are withheld.
A declared `documented` relationship needs a passage establishing the link; that
bridge passage may come from a different source than either endpoint. A declared
`synthesis` needs explicit, scoped reasoning steps and supporting evidence; it
cannot assert historical influence, motivation or independent discovery. Teaching
prerequisites describe concept transfer without asserting scientific necessity.
Legacy files without these declarations retain the earlier common-source admission
rule. Matching a quotation or listing reasoning steps never proves entailment.

The model checks claim support, foundational depth and fidelity to the user's
requested endpoint separately. Accurate related work can remain visible while
losing its `frontier` designation. A company-specific question cannot be satisfied
merely by naming a generic prototype as its result. Each relationship receives a
separate scope, direction and warrant assessment. These are fallible model
judgments, never corpus screening or human review. For bounded_by, the model also classifies the actual endpoint roles; admission requires restricted_claim → restricting_condition regardless of a generic affirmative direction verdict. A premise_for verdict must classify the actual connection as deductive_derivation; design rationale, component use and analogy cannot override this requirement. Imports cross the same local
validation boundary and cannot change registry meanings or the published archive.

Discovery attribution and dates require separate affirmative verdicts. Missing or
negative verdicts clear those fields without deleting an otherwise supported
scientific claim. A historical-basis relationship is withheld if the checked dates
no longer establish earlier-to-later order. Batch-local freeform absence notes are
discarded: checking four claims does not establish what is missing from the whole
map. Record-specific rejection reasons remain visible.

The explanatory core can have parallel dependencies. Navigation must not invent a
linear chain between independent mechanisms or treat one joint premise as
sufficient. The route indicator requires a reachable requested endpoint, at least
four core insights and two non-teaching connections; it measures graph structure,
not scientific truth, completeness or historical influence. A connected route built primarily from teaching links is separately labelled a guided reading path; it never earns a scientific-chain claim. Unexplained inputs,
isolates and withheld links remain visible. A separate reading itinerary may traverse a single-input bounded_by edge toward its restricted method, labelled “bounds”, while preserving the stored arrow and original inspector. This does not satisfy the stricter directed-core metric or permit reversing joint premises.

Streaming previews expose only complete, validated JSON records with matching
source quotations. Their `completion: partial` and `check_status` fields distinguish
unfinished work from a completed model challenge; all remain unverified drafts.
Interrupted requests retain a session-only checkpoint without credentials.
Explicit resume starts the unfinished stage, records another provider receipt,
and preserves completed stages. A saved partial map remains inspectable after
reload, but has no executable checkpoint. Only an explicitly rejected optional provider parameter can trigger a bounded
compatibility retry of the same model. Started generations, timeouts, rate limits
and authentication failures are never automatically replayed; missing usage is
never interpreted as a free request. Each review pass has a shared 60-second deadline, including formatting repair,
with at most four checks in flight. Node checks use batches of at most two insights. Individual completed node verdicts and relationship checks are retained in the
session so manual resumption requests only unfinished checks. At most two follow-ups request only omitted or ambiguous node verdicts within the original review deadline; no completed verdict is rechecked and no provider failure is replayed. Each node and relation needs one unambiguous
verdict before a completed-check label is permitted. An unfinished review leaves
the draft available with incomplete status. Complete source-linked records can
be recovered from interrupted generation, with missing coverage explicitly
recorded before evidence review. No incomplete JSON object is reconstructed.

Planning fixes the requested endpoint and searches for a directly relevant general
principle. The draft has a single result slot and separate foundation and enabling
insight sections. If the first checked map lacks a route,
one targeted semantic refinement can use its feedback and the same sources, if it starts within the first three minutes.
It is a distinct, recorded request, not a replay of a timed-out generation.
Literal template echoes, a completed empty JSON object, or an unmistakable copy of the input packet can consume this same single refinement allowance for one replacement composition; a genuine evidence gap cannot. Input copying is stopped early by exact prefix comparison. These semantic failures skip futile syntax repair; both attempts remain in receipts and unreported usage may be charged. Transport failures and timed-out requests are not replayed. No further automatic refinement loop is allowed. The 24-request session ceiling
includes concurrent requests and manual resumptions; it is not a billing guarantee.

Open-access full-text retrieval uses only fixed Europe PMC endpoints and validated
PMC identifiers. At most three articles are read. Only CC BY or CC0 excerpts with
an explicit license link are admitted by this path; source credit, license and
original excerpt wording accompany saved maps. XML is parsed inertly; entity
instructions, source URLs and article text cannot execute code or grant authority.

General reference acquisition uses the fixed English Wikipedia Action API only.
It tries exact titles before search, with at most
one search fallback per title. Up to eight targeted reference topics cover the canonical technique, a mechanism, three foundations, up to two intermediate route concepts and the original qualified request (or five foundations when no intermediate concepts are proposed), after one initial query overview. Four lookups may run concurrently, each with a shared 20-second deadline. A descriptive mechanism may try one shortened title/search pair within the same deadline. Plain-text excerpts are secondary evidence;
they do not establish experimental validation or original priority. Revision
links, contributor credit and CC BY-SA 4.0 licenses remain attached to quotations
in inspectors and exports. No page-supplied URL is fetched and no markup is
executed. These sources do not become canonical archive records.

Insight writing and connection writing are separate bounded model requests. The
connection pass sees all node claims; writing order never dictates an arrow.
An interrupted connection pass may retain and review only its complete records,
without replaying the request or regenerating insights. An empty optional
refinement preserves the preceding checked result. A teaching relationship is
an explicitly authored concept-transfer interpretation, not a claim that a source
prescribes a curriculum or documents historical influence.

The application assigns disjoint, streaming-stable IDs to the separate insight sections before any arrows are proposed. A connection contract requires at least one existing premise insight, an existing conclusion and exact excerpt identifiers. Qualified single excerpt IDs can be normalized only against the same source; citation ranges remain invalid. General reference retrieval selects bounded complete paragraphs from full bounded plaintext, without the provider's 1,200-character extract parameter. Whitespace-only provider output does not reset the idle timer.

Insight and connection drafting request JSON-object mode after live nested-schema failures. Planning also uses JSON-object mode, with a requested 512-token reasoning allowance; small checks retain strict structured contracts and request 512 reasoning tokens. This changes only the provider format request: local identifiers, exact quotations, supported predicates and independent review remain required. Receipts record the actual format, including on import.

When checked insights survive review, the single optional refinement adds at most two missing or corrected mechanism insights and four candidate connections while preserving unchanged checked records. A missing requested endpoint may use an addition slot only if that role is absent. A foundation may be added when absent or when a distinct required branch needs its own general principle; the original query and endpoint remain authoritative. New insights receive new identities and fresh checks; no rejected insight inherits approval or incident arrows. Only new records receive new checks. Prior verdicts are retained only for the exact unchanged IDs and contents; full insight regeneration clears them. A refinement that yields no usable content cannot erase an earlier checked map.

A canonical reference lookup retains priority when aliases return the same revision. The earlier broad query is recategorized as context before drafting when appropriate; it cannot silently crowd out the canonical explanation. This changes pre-draft passage selection only, never previously anchored records. A revision-specific source-quality ledger can withhold a known conflicting reference and show an explicit warning on older private maps that cite it. Such findings are automated comparisons, not human certification; old map contents are not silently rewritten.

Connection composition validates endpoint IDs and predicate names before evidence review. A completed response with an invalid name can use the bounded allowance of at most two format repairs per exploration, within the same request deadline. Repair receives the existing insight catalog and predicate meanings; it may only recover unambiguous existing intent. It cannot manufacture a relationship, reverse an arrow or convert rejection into approval. Any recovered connection still needs its independent evidence check.

The optional additive refinement can repair a rejected enabling insight or supply a missing operation from already retrieved passages. It has two new insight slots and four new arrow slots. Existing insights and arrows are immutable; new records cannot reuse their identities or their verdicts. A contradictory `bounded_by` check is withheld if the independent node check identifies its destination as the requested method/process rather than a restricting condition.

Reference lookups request disambiguation metadata. A disambiguation list is never a scientific source; its one search fallback uses the planned subject to seek an explanatory article. A concise endpoint heading can add a more specific technology lookup alongside a broad planned topic, within the same eight-topic budget. The original qualified request keeps a reserved lookup. Search hypotheses do not establish equivalence or source quality.

The single bounded refinement can run for a missing main route, an isolated general foundation, or fewer than 80% connected insights. With an existing representative route, it examines warranted links for isolated records without adding more nodes. Missing roles can be restored with new records, but an existing requested result cannot be overwritten or duplicated. This stopping rule does not erase gaps or alter the recorded structural acceptance diagnostic.

Personal-map review conservatively withholds `premise_for` when both its conclusion and all premises are operational methods, mechanisms or representations. When all supplied nodes have those operational kinds, composition omits that ineligible predicate from its proposal vocabulary. This narrows proposals without changing any predicate meaning or granting approval. Numbered component lists and a positive model verdict cannot establish logical implication. Formal arguments and theorems remain eligible for separately checked derivations. This review gate does not silently rewrite imported maps or published corpus records.

A reported empirical observation cannot be established with a `premise_for` deduction; predictions and observations remain separate records. A general empirical claim cannot act as a restricting condition when the independent node check assigned it a general-foundation role. These conservative review gates can leave more gaps and do not certify other retained links. Full-text acquisition reserves one of its three slots for a directly relevant study when available, alongside reviews. The evidence packet reserves space for that study before reference excerpts exhaust its unchanged 24,000-character budget.

Within the unchanged 60-source pool, acquired full-text/reference explanations can displace abstracts. Upgrading an abstract to a full-text study preserves its stable identity and carries its retrieval priority forward before drafting; later abstract metadata cannot downgrade the passage.

During new generation only, a reference ID missing its revision suffix can resolve to the unique retrieved version of that exact page. Multiple versions, explicit wrong revisions, unknown pages and mismatched anchors remain invalid. Resolved evidence stores the full version ID and exact passage before independent claim review. Imports and historical maps do not use this recovery.

Completed drafting JSON is checked for section limits, valid insight objects, compatible roles and allowed subject/kind classifications before assembly. A classification repair preserves the claim and still requires evidence review; source-author credit cannot become discovery attribution through an affirmative model verdict. Misplaced mechanisms cannot be silently discarded by array truncation: the response must pass a bounded format repair or remain unadmitted. This is format recovery, not permission to create claims or bypass evidence review.

For a technological or empirical requested result, the bounded connection composer focuses on documented use, explicit synthesis, limits and teaching links rather than proposing a deduction of the device or observed outcome. Formal theorem endpoints retain deduction proposals. The shared predicate registry, canonical records and independent review meanings are unchanged. During refinement, restoring a missing requested result and general foundation takes priority over optional new mechanisms; unsupported essentials remain gaps.

## Works and selected contributors (catalog version 2 / reader 1.4)

The reader now exposes **subjects → topics → works → insights**. Topic–work and
work–insight membership are many-to-many. A work identifies a paper, book,
technology or bounded research result/program; a Source identifies the actual
inspectable version used as evidence. Broad award citations stay research
programs, with recognition years separate from publication or discovery years.
A catalogue entry without extracted evidence has status `catalogued`; it creates
neither a scientific claim nor a graph connection.

`works.json`, `work_insights.json`, `work_relations.json` and curated `people.json`
are pinned in each release. Their schemas are exported in `schemas/`. Work and
person identities have independent revisions and canonical hashes. Derived counts
and inferred subject memberships are not part of a person's canonical hash.
Sources, work revisions and insight revisions are pinned by reading memberships.
Changed content invalidates the affected interpretation. Additive anchors to
identical source bytes can preserve older pins under the existing enrichment rule.

Only explicitly selected individual profiles enter the current contributor
catalogue. Each requires documentary provenance, a short biography and a selection
reason. Paper author lists never create people. Attribution on an insight remains
verbatim evidence; a source-specific mapping may connect that credit to an already
selected person. Missing profiles do not erase the original credit. Historical
release profiles remain unchanged and reproducible.

Work-level connections are scoped projections of a separately checked insight
relationship, using the same predicate and direction. Endpoints, source anchors
and basis revision must resolve. Joint premises are never flattened into separate
work arrows. Symmetric duplicates are rejected. A shared insight or topic alone
cannot establish influence. A visible example reuses the Cohn–Elkies bound in
Viazovska's sphere-packing work, preserving the original discovery credit and the
separately checked reading rationale.

`/api/search` adds `works` and per-category totals. `/api/works` accepts topic,
person, subject (`pillar`), human-review and pagination filters; `/api/works/{id}`
returns sources, insights, topics, contributors and scoped connections. Existing
inspectors, contributor pages and deterministic briefs include work links. Release
comparisons include catalogue additions, removals and revisions. All responses
retain the release identity and snapshot hash.

The standard offline reader uses SQLite FTS5, accent normalization, bounded spelling recovery,
explicit contributor aliases and a small related-concept registry. At most 16 query
tokens, 120 spelling candidates and six query forms are considered. A whole-name
check resolves some valid-word misspellings without scanning all biographies.
Ambiguous corrections are not arbitrarily chosen. Related concepts are navigation
hints, not equivalence claims; the interface reports expansions. This baseline has no
embedding service or runtime model call. The optional 1.5 server
extension described above adds bounded semantic fallback without promising
unrestricted paraphrase understanding.

## Publishing an accepted frozen snapshot

`promote --from CANDIDATE --id PUBLIC` copies an existing frozen manifest and changes only its `release_id`. It preserves every record revision, catalogue membership, route assessment and source pin; mutable authoring edits cannot enter the publication. The source manifest stays unchanged. Publication uses the same single-writer journal as other immutable admissions, is idempotent for identical content, and refuses to replace an existing identity with different content. Promotion does not switch a running reader; compilation and operational activation are separate steps.
