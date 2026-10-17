import { test, expect } from "@playwright/test";
import {
  validateDraft,
  importExploration,
  type ResearchSource,
} from "../src/explore/model";
import { connectionGaps, lineage, readingRoute } from "../src/explore/lineage";
import { applyReview } from "../src/explore/review";
import {
  localMatches,
  relatedMatches,
  rankLiterature,
  foundationCatalog,
} from "../src/explore/sources";
import { packet } from "../src/explore/agent";
import { excerpts } from "../src/explore/excerpts";
import { assembleConnection, assembleDraft } from "../src/explore/assembly";
import { completedItems, ProviderFailure } from "../src/explore/stream";
import {
  relationVerdict,
  verifyMap,
  checkedNodes,
  type ReviewCheckpoint,
} from "../src/explore/verify";
import { type Provider } from "../src/explore/provider";

test("a complete singleton result survives both streaming and final assembly", () => {
  const result = {
    id: "n1",
    title: "Synthetic endpoint",
    claim: "A complete synthetic endpoint claim.",
    explanation:
      "A full software fixture explanation, not scientific evidence.",
    evidence: [{ source: "fixture", anchor: "p1" }],
  };
  const root = { ...result, title: "Synthetic governing principle" };
  const wire = JSON.stringify({ result, roots: root, steps: [result] });
  const completed = completedItems(wire, "result");
  expect(completed).toEqual([result]);
  expect(
    completedItems(wire.slice(0, wire.indexOf('},"roots"')), "result"),
  ).toEqual([]);
  const final = assembleDraft({ result, roots: root, steps: [result] });
  const streaming = assembleDraft({
    result: completed,
    roots: completedItems(wire, "roots"),
    steps: completedItems(wire, "steps"),
  });
  expect(final.nodes).toEqual(streaming.nodes);
  expect(
    (final.nodes as { id: string; role: string }[]).map((n) => [n.id, n.role]),
  ).toEqual([
    ["roots-1", "foundation"],
    ["steps-1", "bridge"],
    ["result-1", "frontier"],
  ]);
  // An invalid scalar is not reconstructed into a claim.
  expect(
    assembleDraft({ result: "missing", roots: [], steps: [] }).nodes,
  ).toEqual([]);
});

const quotes = [
  "The total momentum of an isolated system remains constant.",
  "Rocket thrust follows from the conservation of momentum of rocket and exhaust.",
  "Controlled rocket thrust decelerates the descending vehicle for landing.",
  "Powered landing permits recovery of the reusable rocket stage.",
];
const sources: ResearchSource[] = quotes.map((quote, i) => ({
  id: `s${i}`,
  title: `Synthetic teaching fixture ${i}`,
  url: `https://example.org/fixture-${i}`,
  authors: [],
  year: null,
  kind: "abstract",
  passage: quote,
  retrieved_at: "fixture",
}));
const registry = {
  applied_in: { layer: "historical", symmetric: false, label: "applied in" },
  premise_for: { layer: "logical", symmetric: false, label: "premise" },
  historical_basis_for: {
    layer: "historical",
    symmetric: false,
    label: "history",
  },
  prerequisite_for_reading: {
    layer: "pedagogical",
    symmetric: false,
    label: "helps explain",
  },
};
function fixture() {
  return {
    title: "Synthetic momentum to recovery route",
    summary: "A controlled test, not a scientific release.",
    nodes: sources.map((s, i) => ({
      id: `n${i}`,
      title: s.title,
      claim: s.passage,
      explanation: s.passage,
      problem: "Explain the next step",
      move: "Apply a scoped physical principle",
      assumptions: [],
      limitations: ["Synthetic fixture"],
      attribution: [],
      year: null,
      subject: "physics",
      kind: "argument",
      role: i === 0 ? "foundation" : i === 3 ? "frontier" : "bridge",
      evidence: [{ source: s.id, quote: quotes[i] }],
    })),
    relations: [1, 2, 3].map((i) => ({
      id: `r${i}`,
      premises: [`n${i - 1}`],
      conclusion: `n${i}`,
      predicate: "applied_in",
      basis: "documented",
      steps: [] as string[],
      warrant: quotes[i],
      scope: "The explicit mechanism described in the synthetic passage.",
      evidence: [{ source: `s${i}`, quote: quotes[i] }],
    })),
    gaps: [],
  };
}

test("generated arrow endpoints preserve direction and joint inputs without changing portable-map fields", () => {
  const raw = fixture();
  const { premises, conclusion, ...relation } = raw.relations[0];
  const normalized = assembleConnection({
    ...relation,
    from: premises,
    to: conclusion,
  });
  expect(normalized.premises).toEqual(premises);
  expect(normalized.conclusion).toBe(conclusion);
  expect(
    validateDraft({ ...raw, relations: [normalized] }, sources, registry)
      .relations,
  ).toHaveLength(1);
  expect(
    assembleConnection({ ...relation, from: ["n0", "n1"], to: "n2" }).premises,
  ).toEqual(["n0", "n1"]);
  const conflicting = assembleConnection({
    ...relation,
    from: ["n0"],
    to: "n1",
    premises: ["n1"],
    conclusion: "n0",
  });
  expect(
    validateDraft({ ...raw, relations: [conflicting] }, sources, registry)
      .relations,
  ).toHaveLength(0);
  expect(assembleConnection(raw.relations[0])).toEqual(raw.relations[0]);
});

test("a documented bridge can cite a different work from the original foundational finding", () => {
  const draft = validateDraft(fixture(), sources, registry);
  expect(draft.nodes).toHaveLength(4);
  expect(draft.relations).toHaveLength(3);
  expect(draft.relations[0].basis).toBe("documented");
  expect(lineage(draft.nodes, draft.relations)).toMatchObject({
    hasBackbone: true,
    route: ["n0", "n1", "n2", "n3"],
    foundations: 1,
    connected: 4,
    scientificSteps: 3,
    isolated: [],
  });
  const bad = fixture();
  bad.relations[0].evidence[0].quote =
    "An invented sentence not present in the evidence.";
  expect(validateDraft(bad, sources, registry).relations).toHaveLength(2);
});

test("a reading itinerary can follow a constraint toward its method without reversing the stored claim", () => {
  const draft = validateDraft(fixture(), sources, registry);
  const relations = [
    { ...draft.relations[0], premises: ["n0"], conclusion: "n1" },
    {
      ...draft.relations[1],
      premises: ["n3"],
      conclusion: "n1",
      predicate: "bounded_by",
      layer: "logical",
    },
    {
      ...draft.relations[2],
      premises: ["n0"],
      conclusion: "n3",
      predicate: "prerequisite_for_reading",
      layer: "pedagogical",
    },
  ];
  const original = structuredClone(relations);
  expect(lineage(draft.nodes, relations).hasBackbone).toBe(false);
  expect(readingRoute(draft.nodes, relations)).toMatchObject({
    route: ["n0", "n1", "n3"],
    reversed: [false, true],
    hasNavigationPath: true,
  });
  expect(relations).toEqual(original);
  // Reversing a joint bound would silently turn conjunctive input into separate
  // sufficient links. The itinerary must not manufacture that traversal.
  relations[1].premises = ["n2", "n3"];
  expect(readingRoute(draft.nodes, relations).hasNavigationPath).toBe(false);
});

test("a qualified exact excerpt is recoverable but ranges and mismatched source prefixes are not", () => {
  const raw = fixture();
  const relation = raw.relations[0] as unknown as { evidence: unknown[] };
  relation.evidence = [{ source: "s1", anchor: "s1:p1" }];
  expect(validateDraft(raw, sources, registry).relations).toHaveLength(3);
  relation.evidence = [{ source: "s1", anchor: "s1:p1-p2" }];
  expect(validateDraft(raw, sources, registry).relations).toHaveLength(2);
  relation.evidence = [{ source: "s1", anchor: "s2:p1" }];
  expect(validateDraft(raw, sources, registry).relations).toHaveLength(2);
});

test("generated reference abbreviations recover only one exact retrieved page version", () => {
  const full = {
    ...sources[0],
    id: "reference_123_456",
    kind: "reference_excerpt" as const,
  };
  const draft = fixture();
  draft.nodes = [draft.nodes[0]];
  draft.relations = [];
  draft.nodes[0].evidence = [{ source: "reference_123", quote: quotes[0] }];
  const validate = (pool = [full]) =>
    validateDraft(draft, pool, registry, { recoverReferenceIds: true });
  expect(validate().nodes[0].evidence).toEqual([
    { source: full.id, quote: quotes[0] },
  ]);
  // Imported/historical content does not opt into generation-only recovery.
  expect(validateDraft(draft, [full], registry).nodes).toHaveLength(0);
  expect(
    validate([full, { ...full, id: "reference_123_789" }]).nodes,
  ).toHaveLength(0);
  expect(validate([{ ...full, id: "reference_1234_456" }]).nodes).toHaveLength(
    0,
  );
  expect(validate([{ ...full, kind: "metadata" as never }]).nodes).toHaveLength(
    0,
  );
  const evidence = draft.nodes[0] as unknown as { evidence: unknown[] };
  for (const anchor of ["p1", "reference_123:p1", "reference_123_456:p1"]) {
    evidence.evidence = [{ source: "reference_123", anchor }];
    expect(validate().nodes[0].evidence[0].source).toBe(full.id);
  }
  for (const anchor of ["p999", "p1-p2", "reference_123_789:p1"]) {
    evidence.evidence = [{ source: "reference_123", anchor }];
    expect(validate().nodes).toHaveLength(0);
  }
  for (const source of ["reference_123_789", "reference_12", full.title]) {
    evidence.evidence = [{ source, quote: quotes[0] }];
    expect(validate().nodes).toHaveLength(0);
  }
  evidence.evidence = [
    {
      source: "reference_123",
      quote: "A fabricated quotation with no source match.",
    },
  ];
  expect(validate().nodes).toHaveLength(0);
});

test("an interrupted backbone retains complete node-and-connection units regardless of key ordering", () => {
  const raw = fixture();
  const backbone = raw.nodes.map((insight, i) => ({
    connection_from_previous: i ? raw.relations[i - 1] : null,
    insight,
  }));
  const interrupted =
    '{"backbone":[' +
    backbone
      .slice(0, 3)
      .map((x) => JSON.stringify(x))
      .join(",") +
    ',{"connection_from_previous":';
  const partial = assembleDraft({
    backbone: completedItems(interrupted, "backbone"),
    branches: [],
  });
  const checked = validateDraft(partial, sources, registry);
  expect(checked.nodes).toHaveLength(3);
  expect(checked.relations).toHaveLength(2);
  const wrong = structuredClone(backbone);
  wrong[2].connection_from_previous!.conclusion = "n3";
  expect(
    validateDraft(assembleDraft({ backbone: wrong }), sources, registry)
      .relations,
  ).toHaveLength(2);
  expect(
    lineage(
      validateDraft(assembleDraft({ backbone }), sources, registry).nodes,
      raw.relations as never,
    ).hasBackbone,
  ).toBe(true);
});

test("a synthesis exposes its derivation and cannot assert historical influence", () => {
  const raw = fixture(),
    r = raw.relations[0];
  r.predicate = "premise_for";
  r.basis = "synthesis";
  expect(validateDraft(raw, sources, registry).relations).toHaveLength(2);
  r.steps = [
    "Apply the cited momentum balance to the rocket and exhaust system.",
    "The exhaust momentum change has an opposing rocket momentum change.",
  ];
  expect(validateDraft(raw, sources, registry).relations).toHaveLength(3);
  // Original endpoint evidence is already present; duplicate citations are not entailment.
  raw.nodes[0].kind = "mechanism";
  raw.nodes[1].kind = "mechanism";
  expect(validateDraft(raw, sources, registry).relations).toHaveLength(3);
  r.steps = [];
  expect(validateDraft(raw, sources, registry).relations).toHaveLength(2);
  r.steps = ["Claim A.", "Claim B."];
  r.predicate = "historical_basis_for";
  expect(validateDraft(raw, sources, registry).relations).toHaveLength(2);
});

test("a third source can document a bridge independently of both original works", () => {
  const raw = fixture();
  const bridge = { ...sources[1], id: "bridge" };
  raw.relations[0].evidence = [{ source: bridge.id, quote: bridge.passage }];
  expect(
    validateDraft(raw, [...sources, bridge], registry).relations,
  ).toHaveLength(3);
  const teaching = raw.relations[0];
  teaching.basis = "teaching";
  teaching.predicate = "applied_in";
  expect(
    validateDraft(raw, [...sources, bridge], registry).relations,
  ).toHaveLength(2);
  teaching.predicate = "prerequisite_for_reading";
  expect(
    validateDraft(raw, [...sources, bridge], registry).relations,
  ).toHaveLength(3);
});

test("excerpt identifiers resolve to bounded verbatim text, never generated quotations", () => {
  const raw = fixture();
  const ref = { source: "s0", anchor: "p1" };
  (raw.nodes[0] as { evidence: unknown[] }).evidence = [ref];
  const checked = validateDraft(raw, sources, registry);
  expect(checked.nodes[0].evidence).toEqual([
    { source: "s0", quote: quotes[0] },
  ]);
  expect(
    excerpts("word ".repeat(100)).every(
      (e) => e.quote.split(/\s+/).length <= 25,
    ),
  ).toBe(true);
  (raw.nodes[0] as { evidence: unknown[] }).evidence = [
    { ...ref, anchor: "invented" },
  ];
  expect(
    validateDraft(raw, sources, registry).nodes.map((n) => n.id),
  ).not.toContain("n0");
});

test("a chain of teaching arrows alone does not qualify as a scientific backbone", () => {
  const draft = validateDraft(fixture(), sources, registry);
  const teaching = draft.relations.map((r) => ({
    ...r,
    predicate: "prerequisite_for_reading",
    layer: "pedagogical",
  }));
  expect(lineage(draft.nodes, teaching)).toMatchObject({
    hasBackbone: false,
    hasReadingPath: true,
    scientificSteps: 0,
  });
  expect(lineage(draft.nodes, [])).toMatchObject({
    hasBackbone: false,
    connected: 0,
    isolated: ["n0", "n1", "n2", "n3"],
  });
  expect(lineage(draft.nodes, draft.relations.slice(1)).hasBackbone).toBe(
    false,
  );
  const ambiguous = draft.nodes.map((n) =>
    n.id === "n2" ? { ...n, role: "frontier" as const } : n,
  );
  expect(lineage(ambiguous, draft.relations).hasBackbone).toBe(false);
  const shortcut = { ...teaching[0], id: "shortcut", conclusion: "n3" };
  expect(lineage(draft.nodes, [shortcut, ...draft.relations]).route).toEqual([
    "n0",
    "n1",
    "n2",
    "n3",
  ]);
  // A useful guided explanation must not disappear behind a direct shortcut,
  // while its pedagogical links still cannot earn a scientific-chain claim.
  expect(
    lineage(draft.nodes, [
      shortcut,
      teaching[0],
      draft.relations[1],
      teaching[2],
    ]),
  ).toMatchObject({
    route: ["n0", "n1", "n2", "n3"],
    hasReadingPath: true,
    hasBackbone: false,
  });
});

test("evidence basis and explanatory roles survive a validated portable map", () => {
  const raw = fixture();
  raw.relations[0].basis = "synthesis";
  raw.relations[0].steps = [
    "Apply the cited momentum balance.",
    "Identify the reaction thrust.",
  ];
  const draft = validateDraft(raw, sources, registry);
  const restored = importExploration(
    JSON.stringify({
      ...draft,
      format: "principia-exploration/v1",
      id: "route-fixture",
      query: "Synthetic rocket route",
      status: "unverified_draft",
      action_scope: "read_only",
      sources,
      receipts: [
        {
          stage: "evidence challenge",
          model: "fixture-model",
          started_at: "2026-10-17T00:00:00Z",
          outcome: "completed",
          input_hash: "a".repeat(64),
          prompt_hash: "b".repeat(64),
          input_tokens: 10,
          output_tokens: 20,
          thinking_disabled: false,
          thinking_budget: 256,
          response_format: "json_object",
        },
      ],
    }),
    registry,
  );
  expect(restored.nodes[0].role).toBe("foundation");
  expect(restored.relations[0].basis).toBe("synthesis");
  expect(restored.relations[0].steps).toHaveLength(2);
  expect(restored.receipts[0]).toMatchObject({
    thinking_disabled: false,
    thinking_budget: 256,
    response_format: "json_object",
  });
  expect(lineage(restored.nodes, restored.relations).hasBackbone).toBe(true);
});

test("foundation names are searched independently and later bridge sources keep packet space", () => {
  const entry = {
    id: "newton",
    revision: 1,
    content_hash: "a",
    title: "Newton's law of conservation of momentum",
    pillar: "physics",
    kind: "argument",
    claim: quotes[0],
    explanation: quotes[0],
    assumptions: [],
    limits: [],
    attribution: [],
    date: { year: null },
  };
  const index = {
    entries: [entry],
    total: 1,
    snapshot_hash: "a",
    release_id: "fixture",
  };
  // The frontier's words alone cannot retrieve this general foundation.
  expect(localMatches(index as never, "SpaceX reusable rockets")).toHaveLength(
    0,
  );
  expect(localMatches(index as never, "conservation of momentum")).toHaveLength(
    1,
  );
  const crowded = Array.from({ length: 24 }, (_, i) => ({
    ...sources[0],
    id: `recent${i}`,
    title: "Recent plasma enhanced chemical vapor deposition application",
    passage: "evidence ".repeat(500),
    search_group: "initial",
  }));
  const bridge = { ...sources[1], search_group: "mechanism" };
  const foundation = { ...sources[2], search_group: "foundation" };
  const selected = packet(
    [...crowded, bridge, foundation],
    "plasma enhanced chemical vapor deposition",
  );
  expect(
    selected
      .find((s) => s.id === bridge.id)
      ?.excerpts.map((e) => e.quote)
      .join(" "),
  ).toBe(bridge.passage);
  expect(
    selected
      .find((s) => s.id === foundation.id)
      ?.excerpts.map((e) => e.quote)
      .join(" "),
  ).toBe(foundation.passage);
  expect(
    selected.reduce(
      (n, s) => n + s.excerpts.reduce((sum, e) => sum + e.quote.length, 0),
      0,
    ),
  ).toBeLessThanOrEqual(36000);
});

test("a relation verdict requires its exact identity and three unambiguous assessments", () => {
  const valid = {
    id: "r1",
    assessment: "The target uses the cited principle.",
    direction: "valid",
    scope: "valid",
    warrant: "supported",
  };
  expect(relationVerdict(valid, "r1").keep).toBe(true);
  for (const field of ["direction", "scope", "warrant"]) {
    expect(relationVerdict({ ...valid, [field]: "unclear" }, "r1").keep).toBe(
      false,
    );
    expect(() => relationVerdict({ ...valid, [field]: true }, "r1")).toThrow();
  }
  expect(() => relationVerdict(valid, "r2")).toThrow();
});

test("a generic approval cannot overrule the endpoint roles of a reversed bound", () => {
  const verdict = {
    id: "bound",
    assessment: "A limit is written before the method.",
    direction: "valid",
    scope: "valid",
    warrant: "supported",
  };
  expect(relationVerdict(verdict, "bound", "bounded_by").keep).toBe(false);
  expect(
    relationVerdict(
      {
        ...verdict,
        endpoint_roles: {
          from: "restricting_condition",
          to: "restricted_claim",
        },
      },
      "bound",
      "bounded_by",
    ).keep,
  ).toBe(false);
  expect(
    relationVerdict(
      {
        ...verdict,
        endpoint_roles: {
          from: "restricted_claim",
          to: "restricting_condition",
        },
      },
      "bound",
      "bounded_by",
    ).keep,
  ).toBe(true);
  expect(relationVerdict(verdict, "bound", "applied_in").keep).toBe(true);
  expect(relationVerdict(verdict, "bound", "premise_for").keep).toBe(false);
  expect(
    relationVerdict(
      { ...verdict, connection_type: "design_rationale" },
      "bound",
      "premise_for",
    ).keep,
  ).toBe(false);
  expect(
    relationVerdict(
      { ...verdict, connection_type: "deductive_derivation" },
      "bound",
      "premise_for",
    ).keep,
  ).toBe(true);
});

test("independent review retains completed checks after a single request fails and never replays them on resume", async () => {
  const draft = validateDraft(fixture(), sources, registry),
    checkpoint: ReviewCheckpoint = { relations: {} };
  const calls: string[] = [],
    deadlines: number[] = [];
  let active = 0,
    maximum = 0,
    failOnce = true;
  const provider = {
    json: async (
      stage: string,
      _prompt: string,
      input: any,
      _tokens: number,
      deadline: number,
    ) => {
      calls.push(stage);
      deadlines.push(deadline);
      maximum = Math.max(maximum, ++active);
      await new Promise((resolve) => setTimeout(resolve, 10));
      active--;
      if (stage === "relation check r2" && failOnce) {
        failOnce = false;
        throw new ProviderFailure("Synthetic interruption");
      }
      if (stage === "evidence challenge")
        return {
          node_checks: input.draft.nodes.map((n: any) => ({
            id: n.id,
            keep: true,
            foundation_general: n.role === "foundation",
            endpoint_matches: n.role === "frontier",
          })),
          relation_checks: [],
          gaps: ["No endpoint appears in this synthetic four-node batch."],
        };
      return {
        id: input.relation.id,
        assessment: "Independent scoped fixture check.",
        direction: "valid",
        scope: "valid",
        warrant: input.relation.id === "r3" ? "unsupported" : "supported",
      };
    },
  } as unknown as Provider;
  const options = {
    provider,
    draft,
    sources,
    query: "Synthetic rocket lineage",
    registry,
    deadline: Date.now() + 60000,
    signal: new AbortController().signal,
    checkpoint,
    packet,
    updated: () => {},
  };
  await expect(verifyMap(options)).rejects.toThrow("Synthetic interruption");
  expect(Object.keys(checkpoint.relations).sort()).toEqual(["r1", "r3"]);
  expect(checkpoint.nodes).toBeDefined();
  const checked = await verifyMap(options);
  expect(calls).toEqual([
    "evidence challenge",
    "evidence challenge",
    "relation check r1",
    "relation check r2",
    "relation check r3",
    "relation check r2",
  ]);
  expect(maximum).toBe(4);
  expect(new Set(deadlines).size).toBe(1);
  expect(checked.relations.map((r) => r.id)).toEqual(["r1", "r2"]);
  expect(checked.gaps.join(" ")).toContain("Connection withheld (r3)");
  expect(checked.gaps.join(" ")).not.toContain("No endpoint appears");
});

test("node review batches stay small and only the interrupted batch is resumed", async () => {
  const draft = validateDraft(fixture(), sources, registry);
  draft.nodes.push(
    ...draft.nodes.slice(1, 3).map((n, i) => ({ ...n, id: `extra-${i}` })),
  );
  draft.relations = [];
  const checkpoint: ReviewCheckpoint = { relations: {} },
    calls: string[][] = [],
    earlier: string[][] = [];
  let interrupt = true;
  const provider = {
    json: async (_stage: string, _prompt: string, input: any) => {
      const batch = input.draft.nodes;
      calls.push(batch.map((n: any) => n.id));
      earlier.push(input.earlier_insights.map((n: any) => n.id));
      if (batch[0].id.startsWith("extra") && interrupt) {
        interrupt = false;
        throw new ProviderFailure("Synthetic stalled batch");
      }
      return {
        node_checks: batch.map((n: any) => ({
          id: n.id,
          keep: true,
          foundation_general: n.role === "foundation",
          endpoint_matches: n.role === "frontier",
        })),
        relation_checks: [],
        gaps: [],
      };
    },
  } as unknown as Provider;
  const options = {
    provider,
    draft,
    sources,
    query: "synthetic",
    registry,
    deadline: Date.now() + 60000,
    signal: new AbortController().signal,
    checkpoint,
    packet,
    updated: () => {},
  };
  await expect(verifyMap(options)).rejects.toThrow("Synthetic stalled batch");
  expect(checkedNodes(checkpoint)).toHaveLength(4);
  const checked = await verifyMap(options);
  expect(checked.nodes).toHaveLength(6);
  expect(earlier).toEqual([
    [],
    ["n0", "n1"],
    ["n0", "n1", "n2", "n3"],
    ["n0", "n1", "n2", "n3"],
  ]);
  expect(calls).toEqual([
    ["n0", "n1"],
    ["n2", "n3"],
    ["extra-0", "extra-1"],
    ["extra-0", "extra-1"],
  ]);
});

test("an omitted node verdict repairs only that record and preserves completed siblings", async () => {
  const draft = validateDraft(fixture(), sources, registry);
  draft.relations = [];
  const checkpoint: ReviewCheckpoint = { relations: {} };
  const calls: string[][] = [];
  const provider = {
    json: async (_stage: string, _prompt: string, input: any) => {
      const ids = input.draft.nodes.map((n: any) => n.id);
      calls.push(ids);
      return {
        node_checks: (calls.length === 1 ? ids.slice(0, -1) : ids).map(
          (id: string) => ({
            id,
            keep: true,
            foundation_general: id === "n0",
            endpoint_matches: id === "n3",
          }),
        ),
        relation_checks: [],
        gaps: [],
      };
    },
  } as unknown as Provider;
  const result = await verifyMap({
    provider,
    draft,
    sources,
    query: "fixture",
    registry,
    deadline: Date.now() + 60000,
    signal: new AbortController().signal,
    checkpoint,
    packet,
    updated: () => {},
  });
  expect(result.nodes).toHaveLength(4);
  expect(calls).toEqual([["n0", "n1"], ["n2", "n3"], ["n1"]]);
  expect(checkedNodes(checkpoint)).toHaveLength(4);
});

test("scholarly homonyms do not displace a matched mechanism", () => {
  const noise = {
    ...sources[0],
    title: "Blood plasma membrane treatment",
    passage: "Clinical plasma samples support biological diagnosis.",
  };
  const mechanism = {
    ...sources[1],
    title: "Plasma enhanced chemical vapor deposition",
    passage: "Plasma activates chemical vapor precursors to deposit a film.",
  };
  expect(
    rankLiterature(
      [noise, mechanism],
      "plasma enhanced chemical vapour deposition fundamentals",
    ),
  ).toEqual([mechanism]);
});

test("an unexplained joint premise cannot be hidden by one connected input", () => {
  const draft = validateDraft(fixture(), sources, registry);
  const orphan = { ...draft.nodes[1], id: "other", role: "bridge" as const };
  draft.relations[1].premises.push(orphan.id);
  expect(lineage([...draft.nodes, orphan], draft.relations).hasBackbone).toBe(
    false,
  );
  expect(
    lineage(
      [...draft.nodes, { ...orphan, role: "foundation" }],
      draft.relations,
    ).hasBackbone,
  ).toBe(true);
});

test("foundational planning chooses from actual atlas records and resolves a field-name alias", () => {
  const base = {
    revision: 1,
    content_hash: "a".repeat(64),
    pillar: "physics",
    kind: "argument",
    explanation: "A classical governing principle.",
    assumptions: [],
    limits: [],
    attribution: [{ name: "Isaac Newton" }],
    date: { year: 1687 },
  };
  const entries = [
    {
      ...base,
      id: "newton",
      title: "Newton's third law as a symmetry principle",
      claim:
        "Forces between interacting bodies form an equal and opposite pair.",
      neighbors: ["rocket"],
    },
    {
      ...base,
      id: "rocket",
      title: "Rocket propulsion via reaction force",
      claim: "The rocket accelerates by transferring momentum to its exhaust.",
      neighbors: ["newton"],
    },
    {
      ...base,
      id: "noise",
      title: "Specialized instrument alignment",
      claim: "A narrow apparatus has been calibrated.",
      neighbors: [],
    },
  ];
  const index = {
    entries,
    total: 3,
    release_id: "fixture",
    snapshot_hash: "fixture",
  } as any;
  expect(foundationCatalog(index).map((e) => e.id)).toEqual(["newton"]);
  const roots = localMatches(index, "Newtonian mechanics", 1, ["physics"]);
  expect(roots[0].atlas_id).toBe("newton");
  expect(
    relatedMatches(index, roots, "rocket propulsion").map((s) => s.atlas_id),
  ).toEqual(["rocket"]);
});

test("atomic graph units retain parallel dependencies without inventing a chain between them", () => {
  const raw = fixture();
  const parallel = [
    { insight: raw.nodes[0], links: [] },
    { insight: raw.nodes[1], links: [raw.relations[0]] },
    {
      insight: raw.nodes[2],
      links: [{ ...raw.relations[1], premises: ["n0"] }],
    },
    {
      insight: raw.nodes[3],
      links: [{ ...raw.relations[2], premises: ["n1", "n2"] }],
    },
  ];
  const d = validateDraft(assembleDraft({ map: parallel }), sources, registry);
  expect(d.nodes).toHaveLength(4);
  expect(d.relations).toHaveLength(3);
  expect(
    d.relations.some((r) => r.premises.includes("n1") && r.conclusion === "n2"),
  ).toBe(false);
  expect(d.relations[2].premises).toEqual(["n1", "n2"]);
  expect(lineage(d.nodes, d.relations).hasBackbone).toBe(true);
  expect(lineage(d.nodes, d.relations).supporting).toHaveLength(1);
  const partial =
    '{"map":[' +
    parallel
      .slice(0, 3)
      .map((p) => JSON.stringify(p))
      .join(",") +
    ',{"insight":';
  const recovered = validateDraft(
    assembleDraft({ map: completedItems(partial, "map") }),
    sources,
    registry,
  );
  expect(recovered.nodes).toHaveLength(3);
  expect(recovered.relations).toHaveLength(2);
});

test("refinement targets the ungrounded entrance to the result branch, not a reachable side branch", () => {
  const draft = validateDraft(fixture(), sources, registry);
  // The fixture is n0 -> n1 -> n2 -> n3. Removing the middle connection
  // leaves n2 as the missing entrance; adding another n0 -> n1 cannot fix it.
  const partial = [draft.relations[0], draft.relations[2]];
  const gaps = connectionGaps(draft.nodes, partial);
  expect(gaps.reachable_from_foundations).toEqual(["n0", "n1"]);
  expect(gaps.ungrounded_result_branch).toEqual(["n2", "n3"]);
  expect(gaps.priority_gap_targets).toEqual(["n2"]);
  expect(
    connectionGaps(draft.nodes, draft.relations).priority_gap_targets,
  ).toEqual([]);
  // A jointly necessary input cannot be omitted just because its co-premise
  // already has a route from a foundation.
  const joint = [
    { ...draft.relations[2], premises: ["n1", "n2"] },
    draft.relations[0],
  ];
  expect(connectionGaps(draft.nodes, joint).priority_gap_targets).toEqual([
    "n2",
  ]);
});

test("a connected substitute does not earn a route to the requested endpoint", () => {
  const draft = validateDraft(fixture(), sources, registry);
  const raw = {
    node_checks: draft.nodes.map((n) => ({
      id: n.id,
      keep: true,
      reason: "",
      foundation_general: n.role === "foundation",
      endpoint_matches: false,
    })),
    relation_checks: draft.relations.map((r) => ({
      id: r.id,
      keep: true,
      scope_matches_endpoints: true,
      direction_correct: true,
      warrant_supported: true,
    })),
    gaps: [],
  };
  const checked = applyReview(raw, draft);
  expect(checked.nodes).toHaveLength(4);
  expect(checked.relations).toHaveLength(3);
  expect(checked.nodes.at(-1)?.role).toBe("bridge");
  expect(lineage(checked.nodes, checked.relations).hasBackbone).toBe(false);
  expect(checked.gaps.join(" ")).toContain("endpoint is still missing");
  raw.node_checks[0].foundation_general = false;
  expect(applyReview(raw, draft).nodes[0].role).toBe("bridge");
});

test("categorical role assessments distinguish a genuine result from related work", () => {
  const draft = validateDraft(fixture(), sources, registry);
  const checks = {
    node_checks: draft.nodes.map((n) => ({
      id: n.id,
      keep: true,
      assessed_role:
        n.role === "foundation"
          ? "general_foundation"
          : n.role === "frontier"
            ? "requested_result"
            : "supporting_idea",
    })),
    relation_checks: draft.relations.map((r) => ({
      id: r.id,
      keep: true,
      direction_correct: true,
      scope_matches_endpoints: true,
      warrant_supported: true,
    })),
    gaps: [],
  };
  expect(
    lineage(applyReview(checks, draft).nodes, draft.relations).hasBackbone,
  ).toBe(true);
  checks.node_checks.at(-1)!.assessed_role = "supporting_idea";
  expect(
    lineage(applyReview(checks, draft).nodes, draft.relations).hasBackbone,
  ).toBe(false);
  checks.node_checks.at(-1)!.assessed_role = "unrecognized";
  expect(() => applyReview(checks, draft)).toThrow();
});

test("role sections preserve the requested endpoint before later streaming content and prevent multiple frontiers", () => {
  const [root, bridge, other, result] = fixture().nodes;
  const content = JSON.stringify({
    // Providers often restart their numbering in each section.
    result: [{ ...result, id: "n1" }],
    roots: [{ ...root, id: "n1" }],
    steps: [
      { ...bridge, id: "n1", role: "frontier" },
      { ...other, id: "n2" },
    ],
  });
  const parsed = assembleDraft({
    result: completedItems(content, "result"),
    roots: completedItems(content, "roots"),
    steps: completedItems(content, "steps"),
  });
  const checked = validateDraft(parsed, sources, registry);
  expect(
    checked.nodes.filter((n) => n.role === "frontier").map((n) => n.id),
  ).toEqual(["result-1"]);
  expect(checked.nodes).toHaveLength(4);
  expect(checked.nodes.find((n) => n.id === "steps-1")?.role).toBe("bridge");
  const partial = content.slice(0, content.indexOf('"steps"'));
  const early = validateDraft(
    assembleDraft({
      result: completedItems(partial, "result"),
      roots: completedItems(partial, "roots"),
      steps: [],
    }),
    sources,
    registry,
  );
  expect(early.nodes.map((n) => n.id)).toEqual(["roots-1", "result-1"]);
  for (const node of early.nodes)
    expect(checked.nodes.find((n) => n.id === node.id)?.claim).toBe(node.claim);
  expect(early.relations).toEqual([]);
});

test("uncertain discovery credit is cleared without deleting a supported foundation", () => {
  const draft = validateDraft(fixture(), sources, registry);
  draft.nodes[0].attribution = ["An exposition author"];
  draft.nodes[0].year = 2025;
  draft.relations = [];
  const result = applyReview(
    {
      node_checks: draft.nodes.map((n) => ({
        id: n.id,
        keep: true,
        foundation_general: true,
        endpoint_matches: true,
        attribution_supported: false,
        date_supported: false,
      })),
      relation_checks: [],
      gaps: [],
    },
    draft,
  );
  expect(result.nodes).toHaveLength(draft.nodes.length);
  expect(result.nodes[0]).toMatchObject({
    role: "foundation",
    attribution: [],
    year: null,
  });
  expect(result.gaps.join(" ")).toContain("left unspecified");
});

test("clearing an unsupported date also withholds the historical claim that depends on it", () => {
  const draft = validateDraft(fixture(), sources, registry);
  draft.nodes[0].year = 1687;
  draft.nodes[1].year = 1903;
  draft.relations[0].predicate = "historical_basis_for";
  const verdicts = {
    node_checks: draft.nodes.map((n) => ({
      id: n.id,
      keep: true,
      foundation_general: true,
      endpoint_matches: true,
      attribution_supported: true,
      date_supported: true,
    })),
    relation_checks: draft.relations.map((r) => ({
      id: r.id,
      keep: true,
      direction_correct: true,
      scope_matches_endpoints: true,
      warrant_supported: true,
    })),
    gaps: [],
  };
  expect(applyReview(verdicts, draft).relations).toHaveLength(3);
  verdicts.node_checks[0].date_supported = false;
  const result = applyReview(verdicts, draft);
  expect(result.nodes).toHaveLength(4);
  expect(result.relations.map((r) => r.id)).toEqual(["r2", "r3"]);
  expect(result.gaps.join(" ")).toContain(
    "Discovery dates were not established",
  );
});
