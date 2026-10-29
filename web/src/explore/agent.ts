import {
  citedSources,
  object,
  strings,
  subjects,
  validateDraft,
  type Exploration,
  type Receipt,
  type Registry,
  type ResearchSource,
} from "./model";
import { EmptyComposition, Provider, requestLimits } from "./provider";
import { checkedNodes, verifyMap, type ReviewCheckpoint } from "./verify";
import { excerpts } from "./excerpts";
import { explanatoryArticles } from "./articles";
import { referenceExplanations } from "./references";
import { connectionGaps, lineage, readingRoute } from "./lineage";
import { assembleConnection, assembleDraft } from "./assembly";
import { isTemplateDraft, compositionRegistry } from "./contracts";
import { additionIds, additionRoles, refinementCandidate } from "./refinement";
import { completedItems, ProviderFailure } from "./stream";
import { type Progress } from "./progress";
import {
  BOUNDARY,
  SCHEMA,
  PLAN,
  DRAFT,
  CONNECT,
  REFINE,
  REFINE_CONNECTIONS,
} from "./prompts";
import {
  atlasIndex,
  atlasSource,
  foundationCatalog,
  matchAtlas as localMatches,
  hydrateAtlas,
  relatedAtlas as relatedMatches,
  mergeSources,
  referenceSources,
  rankLiterature,
  searchLiterature,
} from "./sources";

type Checked = ReturnType<typeof validateDraft>;
type Phase =
  "sources" | "plan" | "follow" | "draft" | "connect" | "review" | "done";
/** Session-only recovery. Deliberately no credential field or automatic persistence. */
export type Checkpoint = {
  id: string;
  created_at: string;
  query: string;
  release: string;
  snapshot: string;
  model: string;
  phase: Phase;
  sources: ResearchSource[];
  gaps: string[];
  queries: string[];
  foundations?: string[];
  foundationId?: string;
  endpoint?: string;
  topic?: string;
  mechanism?: string;
  backbone?: string[];
  subjects?: string[];
  planningQuestions: string[];
  receipts: Receipt[];
  checked?: Checked;
  partial?: Checked;
  reviewIssue?: string;
  reviewChecks?: ReviewCheckpoint;
  refinementAttempted?: boolean;
  refinementFeedback?: Checked;
  connectionRefinement?: boolean;
  templateEcho?: boolean;
  emptyComposition?: boolean;
  inputEcho?: boolean;
  connectionTemplateEcho?: boolean;
  rejectedConnections?: {
    from: string[];
    to: string;
    predicate: string;
    assessment: string;
  }[];
  rejectedInsights?: {
    insight: Checked["nodes"][number];
    assessment: string;
  }[];
};
export function packet(
  sources: ResearchSource[],
  query: string,
  planning = false,
) {
  const terms = query.toLowerCase().match(/[\p{L}\p{N}]{4,}/gu) || [];
  const score = (s: ResearchSource) =>
    terms.reduce((n, t) => n + (s.title.toLowerCase().includes(t) ? 2 : 0), 0);
  const ranked = [...sources].sort(
    (a, b) => Number(!!b.passage) - Number(!!a.passage) || score(b) - score(a),
  );
  // Reserve room for existing explanations and earlier works. Title matching
  // alone otherwise fills the packet with recent papers applying the frontier.
  const atlasRanked = ranked.filter((s) => s.kind === "atlas" && s.passage);
  // Keep the best match to each explicit mechanism search. Otherwise old,
  // tangential works can occupy all reserved slots merely by having an earlier date.
  const mechanisms = new Map<string, ResearchSource[]>();
  for (const s of atlasRanked) {
    if (!s.search_group?.startsWith("foundation: ")) continue;
    const group = s.search_group;
    mechanisms.set(group, [...(mechanisms.get(group) || []), s]);
  }
  const mechanismMatches = [...mechanisms].map(([group, values]) => {
    const words =
      group
        .slice("foundation: ".length)
        .toLowerCase()
        .match(/[\p{L}\p{N}]{3,}/gu) || [];
    const relevance = (s: ResearchSource) =>
      words.reduce(
        (n, word) =>
          n + Number(s.title.toLowerCase().includes(word.replace(/s$/, ""))),
        0,
      );
    return values.sort(
      (a, b) => relevance(b) - relevance(a) || score(b) - score(a),
    )[0];
  });
  const atlasEarlier = atlasRanked
    .filter((s) => s.year !== null)
    .sort((a, b) => a.year! - b.year! || score(b) - score(a))
    .slice(0, planning ? 1 : 3);
  const atlas = [
    ...new Map(
      [
        ...mechanismMatches,
        ...atlasRanked.slice(0, 1),
        ...atlasEarlier,
        ...atlasRanked,
      ].map((s) => [s.id, s]),
    ).values(),
  ].slice(0, planning ? 3 : 7);
  const earlier = ranked
    .filter(
      (s) => s.kind !== "atlas" && s.passage && s.year !== null && score(s) > 0,
    )
    .sort((a, b) => a.year! - b.year! || score(b) - score(a))
    .slice(0, planning ? 2 : 5);
  // Round-robin by research question so an early page of applications cannot
  // crowd out a later search for a fundamental mechanism or a missing bridge.
  const groups = new Map<string, ResearchSource[]>();
  for (const s of ranked) {
    const group = s.search_group || (s.kind === "atlas" ? "atlas" : "initial");
    groups.set(group, [...(groups.get(group) || []), s]);
  }
  const diverse: ResearchSource[] = [];
  for (let i = 0; i < 6; i++)
    for (const group of groups.values()) if (group[i]) diverse.push(group[i]);
  const studies = ranked
    .filter((s) => s.kind === "article_excerpt")
    .sort(
      (a, b) =>
        Number(b.search_group === "selected study") -
        Number(a.search_group === "selected study"),
    );
  const chosen = [
    ...new Map(
      [
        ...ranked.filter((s) => s.search_group === "selected foundation"),
        ...ranked.filter((s) => s.search_group === "technology overview"),
        // Preserve a directly retrieved study before eight reference excerpts
        // can exhaust the packet's character allowance. No extra network call.
        ...(!planning ? studies.slice(0, 1) : []),
        ...ranked
          .filter((s) => s.search_group === "mechanism reference")
          .slice(0, 1),
        // Retrieval is wasted if several long overviews exhaust the packet
        // before the atlas's checked mechanisms reach the model.
        ...atlas.slice(0, planning ? 2 : 4),
        ...earlier.slice(0, 2),
        ...ranked.filter((s) => s.search_group === "enabling reference"),
        ...ranked.filter((s) => s.kind === "reference_excerpt"),
        ...(!planning ? studies.slice(0, 3) : []),
        ...diverse.slice(0, planning ? 4 : 20),
        ...atlas,
        ...earlier,
        ...diverse,
        ...ranked,
      ].map((s) => [s.id, s]),
    ).values(),
  ];
  let remaining = planning ? 6000 : 24000;
  const selected = chosen.slice(0, planning ? 10 : 16);
  return selected
    .map((s, position) => {
      let available = Math.min(
        planning
          ? 650
          : ["foundational reference", "enabling reference"].includes(
                s.search_group || "",
              )
            ? 2400
            : s.search_group === "requested context"
              ? 2000
              : ["article_excerpt", "reference_excerpt"].includes(s.kind)
                ? 5000
                : 2200,
        // Give every selected source a small usable excerpt allocation. This
        // does not create evidence: exact stable excerpt IDs are still checked.
        Math.max(
          0,
          remaining - (selected.length - position - 1) * (planning ? 180 : 600),
        ),
      );
      const anchors = [];
      for (const excerpt of excerpts(s.passage)) {
        if (excerpt.quote.length > available) break;
        anchors.push(excerpt);
        remaining -= excerpt.quote.length;
        available -= excerpt.quote.length;
      }
      return {
        id: s.id,
        title: s.title,
        authors: s.authors.slice(0, 8),
        year: s.year,
        kind: s.kind,
        ...(s.atlas_kind ? { insight_kind: s.atlas_kind } : {}),
        excerpts: anchors,
      };
    })
    .filter((s) => planning || s.excerpts.length > 0);
}
export async function explore(options: {
  query: string;
  key: string;
  model: string;
  release: string;
  registry: Registry;
  signal: AbortSignal;
  progress: (value: Progress) => void;
  receipts: (value: Receipt[]) => void;
  checkpoint: (value: Checkpoint) => void;
  preview: (value: Exploration) => void;
  resume?: Checkpoint;
}): Promise<Exploration> {
  const { signal, registry } = options;
  const query = options.query.trim();
  if (query.length < 2 || query.length > 500)
    throw new Error(
      "Enter a technology, paper or research question in 2–500 characters.",
    );
  if (!options.key.trim() || !options.model.trim())
    throw new Error("Enter your own SiliconFlow API key and a model ID.");
  if (
    options.resume &&
    (options.resume.query !== query ||
      options.resume.release !== options.release)
  )
    throw new Error(
      "The saved step belongs to a different question or atlas snapshot. Start a new exploration.",
    );
  const state: Checkpoint = options.resume
    ? structuredClone(options.resume)
    : {
        id: crypto.randomUUID(),
        created_at: new Date().toISOString(),
        query,
        release: options.release,
        snapshot: "",
        model: options.model,
        phase: "sources",
        sources: [],
        queries: [],
        planningQuestions: [],
        receipts: [],
        gaps: [
          "This is a bounded exploration of retrieved passages and atlas explanations, not an exhaustive literature review or a verified reconstruction of priority.",
        ],
      };
  state.model = options.model;
  let index: Awaited<ReturnType<typeof atlasIndex>> | null = null;
  let progress: Progress = {
    stage: 0,
    detail: "Starting your exploration…",
    stageStarted: Date.now(),
    papers: 0,
    passages: 0,
    atlas: 0,
    insights: (state.checked || state.partial)?.nodes.length || 0,
    connections: (state.checked || state.partial)?.relations.length || 0,
    characters: 0,
    activity: [],
    titles:
      (state.checked || state.partial)?.nodes.map((n) => n.title).slice(-6) ||
      [],
    state: "working",
    foundations: state.foundations,
  };
  const report = (detail?: string, activity?: string) => {
    progress = {
      ...progress,
      ...(detail ? { detail } : {}),
      papers: state.sources.filter((s) => s.kind !== "atlas").length,
      passages: state.sources.filter((s) => !!s.passage).length,
      atlas: state.sources.filter((s) => s.kind === "atlas").length,
      ...(activity
        ? { activity: [...progress.activity, activity].slice(-8) }
        : {}),
    };
    options.progress(progress);
  };
  const stage = (number: number, detail: string) => {
    progress = {
      ...progress,
      stage: number,
      stageStarted: Date.now(),
      refinement: state.refinementAttempted === true,
      characters: 0,
      reviewedInsights: number === 4 ? 0 : undefined,
      reviewedConnections: number === 4 ? 0 : undefined,
      deadline:
        number === 4
          ? Date.now() + requestLimits("evidence challenge").totalMs
          : undefined,
    };
    report(detail, detail);
  };
  const save = () => {
    state.receipts = provider.receipts.map((r) => ({ ...r }));
    options.receipts(state.receipts);
    options.checkpoint({
      ...state,
      sources: [...state.sources],
      gaps: [...state.gaps],
    });
  };
  const map = (checked: Checked, complete = false): Exploration => {
    const coverage = lineage(checked.nodes, checked.relations);
    const itinerary = coverage.hasReadingPath
      ? coverage
      : readingRoute(checked.nodes, checked.relations);
    const routeNames = itinerary.route.map(
      (id) => checked.nodes.find((n) => n.id === id)!.title,
    );
    return {
      format: "principia-exploration/v1",
      id: state.id,
      created_at: state.created_at,
      title: checked.title || query,
      query,
      summary: complete
        ? coverage.hasBackbone
          ? `A reading route from “${routeNames[0]}” to “${routeNames.at(-1)}”, with ${coverage.foundations} foundational ${coverage.foundations === 1 ? "idea" : "ideas"} and ${checked.relations.length} inspectable ${checked.relations.length === 1 ? "connection" : "connections"}. Each connection has its own evidence and assumptions; this is not an exhaustive history or a human-verified account.`
          : itinerary.hasNavigationPath
            ? `A guided reading path from “${routeNames[0]}” to “${routeNames.at(-1)}”. Follow each labelled connection, including the limits on a method. This is not a claim of historical influence or a deductive proof. Inspect the evidence and remaining gaps.`
            : `This search retained ${checked.nodes.length} insights and ${checked.relations.length} connections. A representative path from general foundations to the requested result is still incomplete. Inspect the surviving evidence and the gaps below.`
        : checked.summary,
      atlas_release: state.release,
      snapshot_hash: state.snapshot,
      model: state.model,
      status: "unverified_draft",
      action_scope: "read_only",
      completion: complete ? "complete" : "partial",
      check_status: complete
        ? "completed"
        : state.phase === "review"
          ? "incomplete"
          : "not_started",
      nodes: checked.nodes,
      relations: checked.relations,
      sources: citedSources(state.sources, checked.nodes, checked.relations),
      gaps: [
        ...new Set([
          ...state.gaps,
          ...checked.gaps,
          ...(state.reviewIssue ? [state.reviewIssue] : []),
          ...(!complete
            ? [
                "This is an unfinished map. The evidence challenge has not completed; unreviewed claims or connections may be removed.",
              ]
            : []),
        ]),
      ],
      receipts: provider.receipts.map((r) => ({ ...r })),
    };
  };
  function connectionCandidate(raw: unknown) {
    const value = object(raw);
    return state.connectionRefinement
      ? refinementCandidate(state.refinementFeedback!, value)
      : {
          ...state.checked!,
          relations: (Array.isArray(value.relations)
            ? value.relations
            : []
          ).map(assembleConnection),
          gaps: [...state.checked!.gaps, ...strings(value.gaps, 6)],
        };
  }
  const provider = new Provider(
    options.key.trim(),
    options.model.trim(),
    signal,
    (name, update) => {
      progress = { ...progress, characters: update.characters };
      if (state.phase === "draft" && update.content) {
        const checked = validateDraft(
          assembleDraft({
            title: query,
            summary:
              "A developing research map. Each visible insight has a matching source quotation; the evidence challenge is still pending.",
            ...(["result", "roots"].some((key) =>
              update.content.includes(`"${key}"`),
            )
              ? {
                  result: completedItems(update.content, "result"),
                  roots: completedItems(update.content, "roots"),
                  steps: completedItems(update.content, "steps"),
                }
              : {}),
            nodes: completedItems(update.content, "nodes"),
            relations: completedItems(update.content, "relations"),
            ...(update.content.includes('"map"')
              ? { map: completedItems(update.content, "map") }
              : {}),
            ...(update.content.includes('"backbone"')
              ? {
                  backbone: completedItems(update.content, "backbone"),
                  branches: completedItems(update.content, "branches"),
                }
              : {}),
          }),
          state.sources,
          registry,
          { recoverReferenceIds: true },
        );
        if (checked.nodes.length) {
          state.partial = checked;
          progress = {
            ...progress,
            insights: checked.nodes.length,
            connections: checked.relations.length,
            titles: checked.nodes.map((n) => n.title).slice(-6),
          };
          options.preview(map(checked));
        }
      }
      if (state.phase === "connect" && update.content && state.checked) {
        const checked = validateDraft(
          connectionCandidate({
            additions: completedItems(update.content, "additions"),
            relations: completedItems(update.content, "relations"),
          }),
          state.sources,
          registry,
          { recoverReferenceIds: true },
        );
        state.partial = checked;
        progress = { ...progress, connections: checked.relations.length };
        options.preview(map(checked));
      }
      if (state.phase === "review" && state.checked) {
        progress = {
          ...progress,
          reviewedInsights: checkedNodes(state.reviewChecks).length,
          reviewedConnections: Object.keys(state.reviewChecks?.relations || {})
            .length,
        };
        report(
          `Evidence checked · ${progress.reviewedInsights} / ${state.checked.nodes.length} insights · ${progress.reviewedConnections} / ${state.checked.relations.length} connections${name === "format repair" ? " · repairing response format" : ""}`,
        );
      } else
        report(
          `${name === "format repair" ? "Repairing response formatting" : state.phase === "connect" ? "Connecting the insights through their actual mechanisms" : state.phase === "draft" ? "Writing source-linked insights" : "Choosing targeted follow-up searches"} · ${update.characters > 0 ? `${update.characters.toLocaleString()} characters received` : "organizing the evidence before writing"}`,
        );
      options.receipts(provider.receipts.map((r) => ({ ...r })));
    },
    state.receipts,
  );
  const found = (service: string, incoming: ResearchSource[]) => {
    state.sources = mergeSources(state.sources, incoming);
    report(
      undefined,
      `${service}: ${incoming.length} works, ${incoming.filter((s) => s.passage).length} passages available.`,
    );
  };
  try {
    if (state.phase === "sources") {
      stage(
        0,
        "Searching scholarly indexes and reading the atlas on your device…",
      );
      const initial = await Promise.allSettled([
        atlasIndex(state.release, signal, (loaded, total) =>
          report(
            `Reading the public atlas · ${loaded.toLocaleString()} / ${total.toLocaleString()} insights…`,
          ),
        ),
        searchLiterature(query, signal, found),
        referenceExplanations(query, [], signal),
      ]);
      signal.throwIfAborted();
      if (initial[0].status === "fulfilled") {
        index = initial[0].value;
        state.snapshot = index.snapshot_hash;
        state.sources = mergeSources(
          state.sources,
          await localMatches(index, query, 8, [], signal),
        );
        report(
          undefined,
          `${state.sources.filter((s) => s.kind === "atlas").length} relevant atlas insights found locally.`,
        );
      } else
        state.gaps.push(
          "The public atlas index was unavailable; no atlas insight was inferred from the missing response.",
        );
      if (initial[1].status === "fulfilled")
        state.gaps.push(...initial[1].value.gaps);
      if (initial[2].status === "fulfilled")
        state.sources = mergeSources(
          state.sources,
          initial[2].value.sources.map((s) => ({
            ...s,
            search_group: "requested context",
          })),
        );
      state.phase = "plan";
      save();
    }
    if (state.phase === "plan") {
      stage(
        1,
        "Planning searches for foundations, mechanisms and limitations…",
      );
      try {
        const plan = object(
          await provider.json(
            "research plan",
            BOUNDARY + PLAN,
            {
              query,
              available_foundations: index ? foundationCatalog(index) : [],
              initial_sources: packet(state.sources, query, true),
            },
            1000,
          ),
        );
        if (!Array.isArray(plan.queries))
          throw new ProviderFailure("The research plan was malformed.");
        state.queries = [
          ...new Set(strings(plan.queries, 4).map((q) => q.slice(0, 180))),
        ];
        state.foundations = [
          ...new Set(
            [
              ...(typeof plan.root_principle === "string"
                ? [plan.root_principle]
                : []),
              ...strings(plan.foundations, 5),
            ]
              .map((q) => q.split(/[:(]/)[0].trim().slice(0, 100))
              .filter(Boolean),
          ),
        ]
          .filter(
            (q, i, all) =>
              all.findIndex((x) => x.toLowerCase() === q.toLowerCase()) === i,
          )
          .slice(0, 5);
        const candidate = index?.entries.find(
          (e) => e.id === plan.atlas_foundation_id,
        );
        state.foundationId = candidate?.id;
        state.endpoint =
          typeof plan.endpoint === "string"
            ? plan.endpoint.slice(0, 300)
            : query;
        state.topic =
          typeof plan.topic === "string"
            ? plan.topic.slice(0, 120)
            : state.endpoint.split(":")[0].slice(0, 120);
        state.mechanism =
          typeof plan.mechanism === "string"
            ? plan.mechanism.split(/[:(]/)[0].trim().slice(0, 100)
            : "";
        state.backbone = strings(plan.backbone, 6).map((s) => s.slice(0, 150));
        state.subjects = strings(plan.subjects, 3).filter((s) =>
          subjects.includes(s),
        );
        progress = { ...progress, foundations: state.foundations };
        state.planningQuestions = strings(plan.gaps, 8);
      } catch (error) {
        signal.throwIfAborted();
        if (!(error instanceof ProviderFailure) || !error.recoverable)
          throw error;
        state.queries = [
          `${query.slice(0, 130)} fundamentals mechanism`,
          `${query.slice(0, 130)} limitations evidence`,
        ];
        state.gaps.push(
          "The model's search-planning step was unavailable. Follow-up searches used the original query plus fundamentals/mechanism and limitations/evidence terms.",
        );
        report(
          undefined,
          "Search planning was unavailable; continuing with bounded follow-up searches based on your question.",
        );
      }
      report(undefined, `${state.queries.length} follow-up searches planned.`);
      state.phase = "follow";
      save();
    }
    if (state.phase === "follow") {
      stage(2, "Finding earlier work and checking alternative explanations…");
      if (!index) {
        try {
          index = await atlasIndex(state.release, signal);
        } catch {
          signal.throwIfAborted();
        }
      }
      const root =
        index && state.foundationId
          ? await hydrateAtlas(index, state.foundationId, signal)
          : undefined;
      if (root)
        state.sources = mergeSources(state.sources, [
          { ...atlasSource(root), search_group: "selected foundation" },
        ]);
      if (index && state.subjects?.length) {
        const allowed = new Set(
          index.entries
            .filter((e) => state.subjects!.includes(e.pillar))
            .map((e) => e.id),
        );
        state.sources = state.sources.filter(
          (s) =>
            !s.atlas_id ||
            s.atlas_id === state.foundationId ||
            allowed.has(s.atlas_id),
        );
      }
      if (index)
        for (const concept of [
          ...new Set([...(state.foundations || []), ...(state.backbone || [])]),
        ]) {
          const matches =
            // General foundations may live in another subject. Topic-scoped
            // follow-up searches below retain the planned subject filter.
            (await localMatches(index, concept, 3, [], signal)).map((s) => ({
              ...s,
              search_group: `foundation: ${concept}`,
            }));
          state.sources = mergeSources(state.sources, matches);
          report(
            undefined,
            `Foundation: ${concept} · ${matches.length} atlas explanations`,
          );
        }
      if (index)
        state.sources = mergeSources(
          state.sources,
          await relatedMatches(
            index,
            state.sources.filter((s) => s.kind === "atlas"),
            [query, ...(state.backbone || [])].join(" "),
            6,
            signal,
          ),
        );
      // The plan already covers the defining work, both mechanism transitions
      // and a limit. General principles are retrieved through the reference
      // and local-atlas paths below; repeating them as journal searches adds
      // latency and often retrieves unrelated applications.
      const topic = state.topic || query;
      const searches = [
        ...new Set([
          ...state.queries,
          `${topic} fundamentals review`,
          `${topic} underlying principles mechanism`,
        ]),
      ].slice(0, 4);
      const pending = [...searches];
      // Independent reference reading overlaps literature searches. The shared
      // source transport still caps all outbound retrieval at four requests.
      const referencesPromise = referenceExplanations(
        topic,
        state.foundations || [],
        signal,
        state.mechanism,
        query,
        state.backbone || [],
        { endpoint: state.endpoint, subjects: state.subjects },
      );
      let finished = 0;
      async function worker() {
        while (pending.length) {
          const q = pending.shift()!;
          if (index)
            state.sources = mergeSources(
              state.sources,
              await localMatches(index, q, 2, state.subjects, signal),
            );
          const result = await searchLiterature(
            q,
            signal,
            (service, incoming) =>
              found(
                service,
                rankLiterature(incoming, q)
                  .slice(0, 3)
                  .map((s) => ({ ...s, search_group: q })),
              ),
          );
          state.gaps.push(...result.gaps);
          report(
            `Follow-up searches · ${++finished} / ${searches.length} complete`,
            `Searched: ${q}`,
          );
        }
      }
      // The shared transport bounds requests across both retrieval paths.
      const [references] = await Promise.all([
        referencesPromise,
        worker(),
        worker(),
      ]);
      report(
        "Reading explanations of the technology and its underlying principles…",
      );
      state.sources = mergeSources(state.sources, references.sources);
      state.gaps.push(...references.gaps);
      report(
        undefined,
        `Read ${references.sources.length} general reference explanations; these are secondary sources.`,
      );
      const articles = await explanatoryArticles(
        topic,
        [...(state.foundations || []), ...(state.backbone || [])],
        signal,
        (detail) => report(undefined, detail),
        query,
        state.sources,
      );
      state.sources = mergeSources(state.sources, articles.sources);
      state.gaps.push(...articles.gaps);
      const refs = [
        ...new Set(state.sources.flatMap((s) => s.references || [])),
      ].slice(0, 4);
      let count = 0;
      const followed = await referenceSources(refs, signal, (source) =>
        report(
          `Following cited works · ${++count} / ${refs.length}`,
          source
            ? `Retrieved: ${source.title}`
            : "A cited work was unavailable.",
        ),
      );
      state.sources = mergeSources(state.sources, followed);
      if (followed.length < refs.length)
        state.gaps.push(
          "Some cited works could not be retrieved; their ancestry remains open.",
        );
      if (!state.sources.some((s) => s.passage))
        throw new Error(
          "The searches returned no inspectable passages. The retrieved titles are retained, but cannot support a scientific map.",
        );
      const metadata = state.sources.filter(
        (s) => s.kind === "metadata",
      ).length;
      if (metadata)
        state.gaps.push(
          `${metadata} works provided metadata only and cannot support claim-level evidence.`,
        );
      state.phase = "draft";
      save();
    }
    for (;;) {
      if (state.phase === "draft") {
        stage(
          3,
          state.refinementAttempted
            ? "Strengthening the missing route using the retrieved evidence. One bounded refinement…"
            : "The model is preparing the map. Complete insights will appear as they arrive…",
        );
        let checked: Checked;
        let echoedTemplate = false;
        let emptyComposition = false;
        let inputEcho = false;
        try {
          const raw = await provider.json(
            "draft graph",
            BOUNDARY +
              DRAFT +
              (state.templateEcho
                ? "\nThe previous response copied the illustrative schema's placeholder text. Compose actual insights from the supplied source excerpts. Never return the example field values or source ID placeholders. This is the only replacement composition allowed."
                : "") +
              (state.emptyComposition
                ? state.inputEcho
                  ? "\nThe previous response copied the input packet and was stopped. Return ONLY title, summary, result, roots, steps and gaps. Compose new source-linked insight records. Do not repeat the query fields, registry, sources, source passages or input object. This is the only replacement composition allowed."
                  : "\nThe previous completed response contained no insight records; a glossary or role definition is not an insight. Compose actual source-linked insights from these supplied passages using the requested record shape. If the evidence is insufficient, return empty record arrays with specific evidence gaps. This is the only replacement composition allowed."
                : "") +
              (state.refinementFeedback ? REFINE : "") +
              "\nReturn only this output shape (no sources, registry, schema or input fields): " +
              JSON.stringify({
                title: SCHEMA.title,
                summary: SCHEMA.summary,
                result: [{ ...SCHEMA.nodes[0], role: "frontier" }],
                roots: [{ ...SCHEMA.nodes[0], role: "foundation" }],
                steps: [{ ...SCHEMA.nodes[0], role: "bridge" }],
                gaps: SCHEMA.gaps,
              }),
            {
              query,
              requested_endpoint: query,
              interpreted_endpoint: state.endpoint || query,
              proposed_explanatory_route: state.backbone || [],
              selected_atlas_foundation: state.foundationId || null,
              earlier_planning_questions: state.planningQuestions,
              foundation_search_hypotheses: state.foundations || [],
              ...(state.refinementFeedback
                ? { refinement_feedback: state.refinementFeedback }
                : {}),
              sources: packet(state.sources, query),
            },
            3600,
          );
          const assembled = assembleDraft(raw);
          echoedTemplate = isTemplateDraft(assembled);
          checked = validateDraft(assembled, state.sources, registry, {
            recoverReferenceIds: true,
          });
        } catch (error) {
          signal.throwIfAborted();
          if (error instanceof EmptyComposition) {
            emptyComposition = true;
            inputEcho = error.reason === "input_echo";
            checked = {
              title: "",
              summary: "",
              nodes: [],
              relations: [],
              gaps: [],
            };
          } else {
            // A cut-off response can still contain whole, source-linked records.
            // Review those records; never reconstruct unfinished JSON or replay the draft request.
            if (
              !(error instanceof ProviderFailure) ||
              !error.recoverable ||
              !state.partial?.nodes.length
            )
              throw error;
            checked = {
              ...state.partial,
              summary:
                "A recovered, source-bounded map. Generation ended early; only complete insights with matching source quotations are included. Its coverage is incomplete.",
            };
            state.gaps.push(
              "Map generation ended early. Only complete source-linked insights and connections were recovered and sent for evidence review. Later material may be missing; the generation request was not retried.",
            );
            report(
              undefined,
              `Recovered ${checked.nodes.length} complete insights from an interrupted response; continuing to evidence review.`,
            );
          }
        }
        if (!checked.nodes.length && echoedTemplate) {
          const receipt = [...provider.receipts]
            .reverse()
            .find((r) => r.stage === "draft graph");
          if (receipt) receipt.outcome = "failed";
        }
        if (
          !checked.nodes.length &&
          (echoedTemplate || emptyComposition) &&
          !state.refinementAttempted &&
          Date.now() - Date.parse(state.created_at) < 180_000
        ) {
          state.templateEcho = echoedTemplate;
          state.emptyComposition = emptyComposition;
          state.inputEcho = inputEcho;
          state.refinementAttempted = true;
          const receipt = [...provider.receipts]
            .reverse()
            .find((r) => r.stage === "draft graph");
          if (receipt) receipt.outcome = "failed";
          state.gaps.push(
            `The first drafting response ${inputEcho ? "copied the input packet" : emptyComposition ? "contained no insight records" : "copied example placeholders"} and was rejected. One replacement composition was requested from the same evidence; both attempts are retained in receipts. Unreported usage may still be charged.`,
          );
          save();
          report(
            `The model returned ${inputEcho ? "the input packet" : emptyComposition ? "no insight records" : "example text"} instead of insights. Making one replacement composition from the retrieved evidence…`,
          );
          continue;
        }
        if (!checked.nodes.length && state.refinementFeedback) {
          state.checked = state.refinementFeedback;
          state.gaps.push(
            "The optional refinement returned no usable insights. The earlier checked map is retained; its unresolved gaps remain.",
          );
          state.phase = "done";
          save();
          break;
        }
        if (!checked.nodes.length)
          throw new Error(
            "The response did not contain complete, source-linked insights in the atlas format. The sources are retained; you can retry map creation.",
          );
        state.checked = checked;
        state.reviewChecks = undefined;
        state.partial = undefined;
        state.phase = "connect";
        progress = {
          ...progress,
          insights: checked.nodes.length,
          connections: checked.relations.length,
          titles: checked.nodes.map((n) => n.title).slice(-6),
        };
        save();
        options.preview(map(checked));
      }
      if (state.phase === "connect" && state.checked) {
        stage(
          3,
          state.connectionRefinement
            ? "One final pass for missing connections. Your checked insights remain available below…"
            : "Connecting the full set of insights; independent mechanisms may converge…",
        );
        try {
          const raw = object(
            await provider.json(
              "connect insights",
              BOUNDARY +
                CONNECT +
                (state.connectionTemplateEcho
                  ? "\nThe previous response used literal placeholders such as ellipses instead of warrants. Write actual warranted relationships using the supplied insights and sources. If no link is supported, return an empty relations array with a specific evidence gap. Do not copy the example field values."
                  : "") +
                (state.connectionRefinement ? REFINE_CONNECTIONS : "") +
                "\nReturn ONLY this output shape; never copy nodes, registry, sources or any other input fields: " +
                JSON.stringify({
                  ...(state.connectionRefinement
                    ? {
                        additions: [
                          {
                            ...SCHEMA.nodes[0],
                            id: "addition-1",
                            role: "bridge",
                          },
                        ],
                      }
                    : {}),
                  relations: SCHEMA.relations,
                  gaps: SCHEMA.gaps,
                }),
              {
                query,
                nodes: state.checked.nodes.map(
                  ({
                    id,
                    title,
                    claim,
                    explanation,
                    kind,
                    role,
                    assumptions,
                    limitations,
                    evidence,
                  }) => ({
                    id,
                    title,
                    claim,
                    explanation,
                    kind,
                    role,
                    assumptions,
                    limitations,
                    evidence,
                  }),
                ),
                ...(state.connectionRefinement
                  ? {
                      refinement: {
                        addition_ids: additionIds,
                        allowed_roles: additionRoles(state.checked.nodes),
                        missing_essentials: [
                          ...(!state.checked.nodes.some(
                            (n) => n.role === "frontier",
                          )
                            ? [
                                "Restore the exact requested result with the stated defect corrected; this is the first addition priority.",
                              ]
                            : []),
                          ...(!state.checked.nodes.some(
                            (n) => n.role === "foundation",
                          )
                            ? [
                                "Restore a source-supported general principle, stated without an unsupported application clause; this is the next addition priority.",
                              ]
                            : []),
                        ],
                        max_additions: 2,
                        max_relations: 4,
                      },
                      rejected_insights: state.rejectedInsights,
                      endpoint: state.endpoint || query,
                      planned_route: state.backbone,
                      route_diagnostics: {
                        ...connectionGaps(
                          state.checked.nodes,
                          state.checked.relations,
                        ),
                        foundation_ids: state.checked.nodes
                          .filter((n) => n.role === "foundation")
                          .map((n) => n.id),
                        result_ids: state.checked.nodes
                          .filter((n) => n.role === "frontier")
                          .map((n) => n.id),
                        unreachable_from_foundations: lineage(
                          state.checked.nodes,
                          state.checked.relations,
                        ).unreachable,
                      },
                      accepted_relations:
                        state.refinementFeedback?.relations.map(
                          ({ premises, conclusion, ...r }) => ({
                            ...r,
                            from: premises,
                            to: conclusion,
                          }),
                        ),
                      rejected_connections: state.rejectedConnections,
                    }
                  : {}),
                registry: compositionRegistry(state.checked.nodes, registry),
                // A bridge can be explained by a different passage from either
                // endpoint. Keep that evidence available to the connection pass.
                sources: packet(state.sources, query),
                ...(state.refinementFeedback
                  ? {
                      earlier_feedback: state.refinementFeedback.gaps
                        .filter((gap) =>
                          /^(?:Connection withheld|Insight withheld|A proposed connection was withheld)|deeper governing principle|exact requested result/.test(
                            gap,
                          ),
                        )
                        .slice(-12),
                    }
                  : {}),
              },
              state.connectionRefinement ? 2600 : 2200,
            ),
          );
          const relations = Array.isArray(raw.relations) ? raw.relations : [];
          if (
            relations.length &&
            relations.every((r) =>
              ["...", SCHEMA.relations[0].warrant].includes(
                String(object(r).warrant),
              ),
            )
          ) {
            const receipt = [...provider.receipts]
              .reverse()
              .find((r) => r.stage === "connect insights");
            if (receipt) receipt.outcome = "failed";
            if (
              !state.refinementAttempted &&
              Date.now() - Date.parse(state.created_at) < 180_000
            ) {
              state.connectionTemplateEcho = true;
              state.refinementAttempted = true;
              state.partial = undefined;
              state.gaps.push(
                "The first connection response contained literal placeholders and was rejected. One replacement composition was requested; both requests and their usage are retained.",
              );
              save();
              report(
                "The model returned placeholders for the connections. Making one replacement composition while preserving your insights…",
              );
              continue;
            }
            throw new ProviderFailure(
              "The model returned placeholders instead of evidenced connections. Your insights and sources are retained; no placeholder arrow was admitted.",
            );
          }
          state.checked = validateDraft(
            connectionCandidate(raw),
            state.sources,
            registry,
            { recoverReferenceIds: true },
          );
        } catch (error) {
          signal.throwIfAborted();
          if (
            !(error instanceof ProviderFailure) ||
            !error.recoverable ||
            !state.partial?.relations.length
          )
            throw error;
          state.checked = state.partial;
          state.gaps.push(
            "Connection generation ended early. Only whole source-linked connections were retained and checked; the request was not replayed.",
          );
        }
        state.partial = undefined;
        state.phase = "review";
        progress = { ...progress, connections: state.checked.relations.length };
        save();
        options.preview(map(state.checked));
      }
      if (state.phase === "review" && state.checked) {
        state.reviewIssue = undefined;
        stage(
          4,
          "Your draft is ready below. Checking its claims and connections; this step is limited to 60 seconds.",
        );
        const checked = state.checked;
        state.reviewChecks ||= { relations: {} };
        state.checked = await verifyMap({
          provider,
          draft: checked,
          sources: state.sources,
          query,
          endpoint: state.endpoint,
          registry,
          deadline: progress.deadline!,
          signal,
          checkpoint: state.reviewChecks,
          packet,
          updated: () => {
            progress = {
              ...progress,
              reviewedInsights: checkedNodes(state.reviewChecks).length,
              reviewedConnections: Object.keys(
                state.reviewChecks?.relations || {},
              ).length,
            };
            save();
            report(
              `Evidence checked · ${progress.reviewedInsights} / ${checked.nodes.length} insights · ${progress.reviewedConnections} / ${checked.relations.length} connections`,
            );
          },
        });
        progress = {
          ...progress,
          reviewedInsights: checked.nodes.length,
          reviewedConnections: checked.relations.length,
        };
        if (
          state.refinementFeedback?.relations.length &&
          !state.checked.relations.length
        ) {
          // Both maps have been checked independently. A failed optional
          // refinement must not erase the earlier useful, inspected links.
          state.checked = state.refinementFeedback;
          state.gaps.push(
            "The optional refinement produced no retained connections. The earlier checked map is preserved with its remaining gaps.",
          );
        }
        save();
        const route = lineage(state.checked.nodes, state.checked.relations);
        if (
          (!route.hasBackbone ||
            route.connected < state.checked.nodes.length * 0.8 ||
            state.checked.nodes.some(
              (n) => n.role === "foundation" && route.isolated.includes(n.id),
            )) &&
          !state.refinementAttempted &&
          Date.now() - Date.parse(state.created_at) < 180_000 &&
          provider.receipts.length <= (state.checked.nodes.length ? 17 : 12) &&
          state.foundations?.length
        ) {
          state.refinementAttempted = true;
          state.refinementFeedback = state.checked;
          const retainedNodes = new Set(state.checked.nodes.map((n) => n.id));
          state.rejectedInsights = checked.nodes
            .filter((n) => !retainedNodes.has(n.id))
            .map((insight) => ({
              insight,
              assessment: String(
                object(
                  checkedNodes(state.reviewChecks).find(
                    (v) => object(v).id === insight.id,
                  ),
                ).reason || "Withheld during review",
              ),
            }));
          state.rejectedConnections = checked.relations
            .filter(
              (r) =>
                !state.checked!.relations.some(
                  (accepted) => accepted.id === r.id,
                ),
            )
            .map((r) => ({
              from: r.premises,
              to: r.conclusion,
              predicate: r.predicate,
              assessment: String(
                state.reviewChecks?.relations[r.id]?.reason ||
                  "Withheld during review",
              ),
            }));
          state.connectionRefinement = state.checked.nodes.length > 0;
          // Reuse verdicts only for the exact unchanged records. New arrows
          // receive new IDs and their own independent review.
          if (state.connectionRefinement && state.reviewChecks) {
            const nodes = new Set(state.checked.nodes.map((n) => n.id));
            const relations = new Set(state.checked.relations.map((r) => r.id));
            state.reviewChecks = {
              nodes: {
                ...state.reviewChecks.nodes,
                node_checks: checkedNodes(state.reviewChecks).filter((n) =>
                  nodes.has(String(object(n).id)),
                ),
              },
              relations: Object.fromEntries(
                Object.entries(state.reviewChecks.relations).filter(([id]) =>
                  relations.has(id),
                ),
              ),
            };
          }
          state.phase = state.connectionRefinement ? "connect" : "draft";
          state.gaps.push(
            state.connectionRefinement
              ? "One refinement examined missing mechanisms and connections using the already retrieved evidence and review feedback. Checked insights and existing links were preserved. Any added insight and connection received a new check."
              : "The first map had an incomplete explanatory route or unconnected insights. One targeted refinement was attempted using the same retrieved evidence and the previous check’s feedback.",
          );
          options.preview(map(state.checked));
          continue;
        }
        state.phase = "done";
        save();
      }
      break;
    }
    signal.throwIfAborted();
    progress = {
      ...progress,
      state: "complete",
      deadline: undefined,
      insights: state.checked!.nodes.length,
      connections: state.checked!.relations.length,
      titles: state.checked!.nodes.map((n) => n.title).slice(-6),
    };
    const finalCoverage = lineage(
      state.checked!.nodes,
      state.checked!.relations,
    );
    report(
      finalCoverage.hasBackbone
        ? "The explanatory map is ready. Inspect the evidence before relying on this draft."
        : readingRoute(state.checked!.nodes, state.checked!.relations)
              .hasNavigationPath
          ? "A guided reading path is available below. The scientific and historical connections still have gaps."
          : "This search is finished, but a foundation-to-result route is still incomplete.",
    );
    return map(state.checked!, true);
  } catch (error) {
    progress = { ...progress, state: "paused" };
    report(
      signal.aborted
        ? "Paused. Your completed work is retained in this tab."
        : state.phase === "review"
          ? "The evidence review stopped. Your draft is available below; its review remains incomplete. You can save it or resume this check."
          : "This step stopped. Your completed work is retained in this tab.",
    );
    const partial =
      state.phase === "connect"
        ? state.partial || state.checked
        : state.checked || state.partial;
    if (partial?.nodes.length) options.preview(map(partial));
    if (
      !signal.aborted &&
      state.phase === "review" &&
      state.checked &&
      error instanceof ProviderFailure &&
      error.recoverable
    ) {
      state.reviewIssue = `Evidence review incomplete: ${error.message} These records remain unverified; no completed review is claimed.`;
      return map(state.checked);
    }
    throw error;
  } finally {
    save();
    provider.clear();
  }
}
