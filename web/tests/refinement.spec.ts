import { test, expect } from "@playwright/test";
import { refinementCandidate } from "../src/explore/refinement";
import {
  connectionContractErrors,
  draftContractErrors,
  compositionRegistry,
} from "../src/explore/contracts";
import { applyReview } from "../src/explore/review";
import {
  Provider,
  EmptyComposition,
  echoesInput,
} from "../src/explore/provider";
import type { validateDraft } from "../src/explore/model";

test("an unmistakable streamed input echo stops without spending a format repair or admitting source records", async () => {
  const input = {
    query: "A discovery",
    requested_endpoint: "A discovery",
    sources: [{ id: "s1", passage: "Source text. ".repeat(100) }],
  };
  const body = JSON.stringify(input);
  expect(echoesInput(body.slice(0, 400), body)).toBe(true);
  expect(echoesInput(body.slice(0, 40), body)).toBe(false);
  expect(
    echoesInput(
      JSON.stringify({ title: "Actual output", roots: [{ claim: body }] }),
      body,
    ),
  ).toBe(false);
  const original = globalThis.fetch;
  let calls = 0;
  globalThis.fetch = async () => {
    calls++;
    return new Response(
      JSON.stringify({
        choices: [{ message: { content: body }, finish_reason: "stop" }],
      }),
      { headers: { "Content-Type": "application/json" } },
    );
  };
  try {
    const provider = new Provider(
      "fixture-key",
      "fixture/input-echo",
      new AbortController().signal,
    );
    await expect(
      provider.json("draft graph", "Fixture", input, 500),
    ).rejects.toBeInstanceOf(EmptyComposition);
    expect(calls).toBe(1);
    expect(provider.receipts[0].outcome).toBe("failed");
    expect(provider.receipts[0].input_tokens).toBeNull();
  } finally {
    globalThis.fetch = original;
  }
});

test("a completed role glossary does not waste a format repair on absent insights", async () => {
  const original = globalThis.fetch;
  let calls = 0;
  globalThis.fetch = async () => {
    calls++;
    return new Response(
      JSON.stringify({
        model: "fixture/role-glossary",
        choices: [
          {
            message: {
              content: JSON.stringify({
                foundation:
                  "states a general principle that applies beyond this technology.",
              }),
            },
            finish_reason: "stop",
          },
        ],
        usage: { prompt_tokens: 30, completion_tokens: 20 },
      }),
      { headers: { "Content-Type": "application/json" } },
    );
  };
  try {
    const provider = new Provider(
      "fixture-key",
      "fixture/role-glossary",
      new AbortController().signal,
    );
    await expect(
      provider.json("draft graph", "Fixture", {}, 500),
    ).rejects.toBeInstanceOf(EmptyComposition);
    expect(calls).toBe(1);
    expect(provider.receipts[0].input_tokens).toBe(30);
    expect(provider.receipts[0].outcome).toBe("failed");
  } finally {
    globalThis.fetch = original;
  }
});

test("operational composition excludes already-ineligible deductions without changing registry meanings", () => {
  const registry = {
    premise_for: { layer: "logical", symmetric: false },
    applied_in: { layer: "logical", symmetric: false },
    prerequisite_for_reading: { layer: "pedagogical", symmetric: false },
  };
  const narrowed = compositionRegistry(
    [{ kind: "mechanism" }, { kind: "method" }],
    registry,
  );
  expect(narrowed).not.toHaveProperty("premise_for");
  expect(narrowed.applied_in).toBe(registry.applied_in);
  expect(
    compositionRegistry(
      [
        { kind: "theorem", role: "foundation" },
        { kind: "mechanism", role: "frontier" },
      ],
      registry,
    ),
  ).not.toHaveProperty("premise_for");
  expect(
    compositionRegistry(
      [
        { kind: "theorem", role: "foundation" },
        { kind: "empirical_finding", role: "frontier" },
      ],
      registry,
    ),
  ).not.toHaveProperty("premise_for");
  expect(
    compositionRegistry(
      [
        { kind: "theorem", role: "foundation" },
        { kind: "theorem", role: "frontier" },
      ],
      registry,
    ),
  ).toBe(registry);
  expect(registry).toHaveProperty("premise_for");
  expect(
    compositionRegistry([{ kind: "theorem" }, { kind: "method" }], registry),
  ).toBe(registry);
});

test("misplaced draft sections receive a format repair instead of losing the mechanisms", async () => {
  const root = {
    claim: "A general principle",
    role: "foundation",
    subject: "physics",
    kind: "mechanism",
  };
  const bridge = {
    claim: "A source-linked mechanism",
    role: "bridge",
    subject: "physics",
    kind: "mechanism",
  };
  const result = {
    claim: "The requested operation",
    role: "frontier",
    subject: "physics",
    kind: "method",
  };
  const malformed = { roots: [root, "steps,[{", bridge], result, gaps: [] };
  const repaired = { roots: [root], steps: [bridge], result, gaps: [] };
  expect(draftContractErrors(malformed).length).toBeGreaterThan(0);
  expect(draftContractErrors(repaired)).toEqual([]);
  expect(
    draftContractErrors({
      roots: [],
      result: [],
      steps: [],
      gaps: ["No evidence"],
    }),
  ).toEqual([]);
  const original = globalThis.fetch;
  let calls = 0;
  globalThis.fetch = async () => {
    calls++;
    return new Response(
      JSON.stringify({
        model: "fixture/draft-sections",
        choices: [
          {
            message: {
              content: JSON.stringify(calls === 1 ? malformed : repaired),
            },
            finish_reason: "stop",
          },
        ],
      }),
      { headers: { "Content-Type": "application/json" } },
    );
  };
  try {
    const provider = new Provider(
      "fixture-key",
      "fixture/draft-sections",
      new AbortController().signal,
    );
    const actual = await provider.json(
      "draft graph",
      "Fixture",
      { sources: [] },
      500,
    );
    expect(actual).toEqual(repaired);
    expect(calls).toBe(2);
    expect(provider.receipts.map((r) => r.outcome)).toEqual([
      "failed",
      "completed",
    ]);
  } finally {
    globalThis.fetch = original;
  }
});

test("refinement cannot overwrite checked identities, invent a new endpoint or inherit an old verdict", () => {
  const base = {
    title: "Fixture",
    summary: "Fixture",
    nodes: [
      { id: "n1", role: "foundation", claim: "Original" },
      { id: "n2", role: "frontier", claim: "Original result" },
    ],
    relations: [],
    gaps: [],
  } as unknown as ReturnType<typeof validateDraft>;
  const merged = refinementCandidate(base, {
    additions: [
      { id: "n1", role: "bridge", claim: "Changed" },
      { id: "addition-1", role: "frontier", claim: "Different endpoint" },
    ],
  });
  expect(merged.nodes).toEqual(base.nodes);
  expect(merged.gaps).toHaveLength(2);
  expect(base.gaps).toEqual([]);
  const candidate = refinementCandidate(base, {
    additions: [
      { id: "addition-1", role: "bridge", claim: "New unverified claim" },
    ],
  });
  expect(candidate.nodes).toHaveLength(3);
  expect(candidate.nodes[0]).toEqual(base.nodes[0]);
});

test("classification mistakes are repaired without silently losing a scientific foundation", async () => {
  const root = {
    id: "n1",
    title: "Photon absorption",
    claim: "Absorbed photons can initiate chemical reactions.",
    subject: "chemistry",
    kind: "mechanism",
    role: "foundation",
  };
  const invalid = { roots: [root], steps: [], result: [], gaps: [] };
  const corrected = { ...invalid, roots: [{ ...root, subject: "physics" }] };
  expect(draftContractErrors(invalid).join(" ")).toContain("subject=chemistry");
  expect(draftContractErrors(corrected)).toEqual([]);
  expect(
    draftContractErrors({
      ...invalid,
      roots: [{ ...root, subject: "physics", kind: "device" }],
    }).join(" "),
  ).toContain("kind=device");
  const original = globalThis.fetch;
  let calls = 0;
  globalThis.fetch = async (_url, init) => {
    const request = JSON.parse(String(init?.body));
    if (++calls === 2)
      expect(request.messages[1].content).toContain("subject=chemistry");
    return new Response(
      JSON.stringify({
        choices: [
          {
            message: {
              content: JSON.stringify(calls === 1 ? invalid : corrected),
            },
            finish_reason: "stop",
          },
        ],
      }),
      { headers: { "Content-Type": "application/json" } },
    );
  };
  try {
    const provider = new Provider(
      "fixture-key",
      "fixture/classification",
      new AbortController().signal,
    );
    expect(await provider.json("draft graph", "Fixture", {}, 500)).toEqual(
      corrected,
    );
    expect(calls).toBe(2);
    expect(provider.receipts.map((r) => r.outcome)).toEqual([
      "failed",
      "completed",
    ]);
  } finally {
    globalThis.fetch = original;
  }
});

test("connection format validation separates insight IDs, source IDs and evidence-basis labels", () => {
  const input = {
    nodes: [{ id: "roots-1" }, { id: "result-1" }],
    registry: { prerequisite_for_reading: {} },
  };
  const invalid = {
    relations: [
      {
        id: "r1",
        from: ["reference_123"],
        to: "result-1",
        predicate: "teaching",
      },
    ],
  };
  expect(connectionContractErrors(invalid, input)).toHaveLength(2);
  const valid = {
    relations: [
      {
        id: "r1",
        from: ["roots-1"],
        to: "result-1",
        predicate: "prerequisite_for_reading",
      },
    ],
  };
  expect(connectionContractErrors(valid, input)).toEqual([]);
  expect(
    connectionContractErrors(
      {
        additions: [
          { id: "addition-1", subject: "physics", kind: "mechanism" },
        ],
        relations: [{ ...valid.relations[0], to: "addition-1" }],
      },
      { ...input, refinement: true },
    ),
  ).toEqual([]);
  expect(
    connectionContractErrors(
      { relations: [{ ...valid.relations[0], to: "addition-1" }] },
      { ...input, refinement: true },
    ),
  ).toHaveLength(1);
});

test("a vocabulary mistake uses one bounded format repair and never silently substitutes a predicate", async () => {
  const original = globalThis.fetch;
  let calls = 0;
  const model = "fixture/relationship-format",
    bodies: any[] = [];
  globalThis.fetch = async (_url, init) => {
    const body = JSON.parse(String(init?.body));
    bodies.push(body);
    calls++;
    return new Response(
      JSON.stringify({
        model,
        choices: [
          {
            message: {
              content: JSON.stringify({
                relations: [
                  {
                    id: "r1",
                    from: ["n1"],
                    to: "n2",
                    predicate:
                      calls === 1 ? "teaching" : "prerequisite_for_reading",
                  },
                ],
                gaps: [],
              }),
            },
            finish_reason: "stop",
          },
        ],
        usage: { prompt_tokens: 12, completion_tokens: 20 },
      }),
      { headers: { "Content-Type": "application/json" } },
    );
  };
  try {
    const provider = new Provider(
      "fixture-key",
      model,
      new AbortController().signal,
    );
    const result: any = await provider.json(
      "connect insights",
      "Fixture",
      {
        nodes: [
          { id: "n1", claim: "Specific concept" },
          { id: "n2", claim: "An operation using that concept" },
        ],
        registry: {
          prerequisite_for_reading: { meaning: "Authored reading aid" },
        },
      },
      100,
    );
    expect(calls).toBe(2);
    expect(result.relations[0].predicate).toBe("prerequisite_for_reading");
    const repair = JSON.parse(bodies[1].messages[1].content);
    expect(repair.known_insights).toHaveLength(2);
    expect(repair.format_error).toContain("invalid predicate=teaching");
    expect(provider.receipts.map((r) => [r.stage, r.outcome])).toEqual([
      ["connect insights", "failed"],
      ["format repair", "completed"],
    ]);
  } finally {
    globalThis.fetch = original;
  }
});

test("reference credit cannot become discovery attribution through an affirmative model verdict", () => {
  const draft = {
    title: "Credit fixture",
    summary: "",
    gaps: [],
    relations: [],
    nodes: [
      {
        id: "reference",
        title: "General principle",
        kind: "mechanism",
        role: "foundation",
        attribution: ["Wikipedia contributors"],
        year: null,
      },
      {
        id: "person",
        title: "Another principle",
        kind: "theorem",
        role: "foundation",
        attribution: ["Isaac Newton"],
        year: null,
      },
    ],
  } as unknown as ReturnType<typeof validateDraft>;
  const checked = applyReview(
    {
      node_checks: draft.nodes.map((n) => ({
        id: n.id,
        keep: true,
        assessed_role: "general_foundation",
        attribution_supported: true,
        date_supported: false,
      })),
      relation_checks: [],
      gaps: [],
    },
    draft,
  );
  expect(checked.nodes[0].attribution).toEqual([]);
  expect(checked.nodes[1].attribution).toEqual(["Isaac Newton"]);
  expect(draft.nodes[0].attribution).toEqual(["Wikipedia contributors"]);
});

test("a limiting arrow cannot override a separate verdict identifying its destination as the requested process", () => {
  const draft = {
    title: "Fixture",
    summary: "Fixture",
    gaps: [],
    nodes: [
      {
        id: "limit",
        kind: "theorem",
        role: "foundation",
        attribution: [],
        year: null,
      },
      {
        id: "result",
        kind: "mechanism",
        role: "frontier",
        attribution: [],
        year: null,
      },
    ],
    relations: [
      {
        id: "wrong",
        premises: ["limit"],
        conclusion: "result",
        predicate: "bounded_by",
      },
    ],
  } as unknown as ReturnType<typeof validateDraft>;
  const node_checks = [
    { id: "limit", keep: true, assessed_role: "general_foundation" },
    { id: "result", keep: true, assessed_role: "requested_result" },
  ];
  const verdict = {
    id: "wrong",
    keep: true,
    direction_correct: true,
    scope_matches_endpoints: true,
    warrant_supported: true,
  };
  const checked = applyReview(
    { node_checks, relation_checks: [verdict], gaps: [] },
    draft,
  );
  expect(checked.relations).toEqual([]);
  expect(checked.gaps.join(" ")).toContain("contradictory limiting arrow");
  const proper = {
    ...draft,
    relations: [
      { ...draft.relations[0], premises: ["result"], conclusion: "limit" },
    ],
  };
  expect(
    applyReview({ node_checks, relation_checks: [verdict], gaps: [] }, proper)
      .relations,
  ).toHaveLength(1);
});

test("numbered component lists cannot pass as deductions even with a positive model verdict", () => {
  const draft = {
    title: "Fixture",
    summary: "Fixture",
    gaps: [],
    nodes: [
      {
        id: "component",
        kind: "mechanism",
        role: "bridge",
        attribution: [],
        year: null,
      },
      {
        id: "process",
        kind: "mechanism",
        role: "frontier",
        attribution: [],
        year: null,
      },
    ],
    relations: [
      {
        id: "inference",
        premises: ["component"],
        conclusion: "process",
        predicate: "premise_for",
        steps: [
          "The process uses this component.",
          "The component belongs to the process.",
        ],
      },
    ],
  } as unknown as ReturnType<typeof validateDraft>;
  const review = {
    node_checks: [
      { id: "component", keep: true, assessed_role: "supporting_idea" },
      { id: "process", keep: true, assessed_role: "requested_result" },
    ],
    relation_checks: [
      {
        id: "inference",
        keep: true,
        direction_correct: true,
        scope_matches_endpoints: true,
        warrant_supported: true,
      },
    ],
    gaps: [],
  };
  const checked = applyReview(review, draft);
  expect(checked.nodes).toHaveLength(2);
  expect(checked.relations).toEqual([]);
  expect(checked.gaps.join(" ")).toContain("Operational components alone");
  expect(draft.relations).toHaveLength(1);
  const application = {
    ...draft,
    relations: [{ ...draft.relations[0], predicate: "applied_in" }],
  };
  expect(applyReview(review, application).relations).toHaveLength(1);
  const formal = {
    ...draft,
    nodes: [{ ...draft.nodes[0], kind: "theorem" as const }, draft.nodes[1]],
  };
  expect(applyReview(review, formal).relations).toHaveLength(1);
});

test("an observed speedup is not deduced from a broad hardware claim or reversed into its bound", () => {
  const draft = {
    title: "Fixture",
    summary: "Fixture",
    gaps: [],
    nodes: [
      {
        id: "hardware",
        title: "Broad hardware claim",
        kind: "empirical_finding",
        role: "foundation",
        attribution: [],
        year: null,
      },
      {
        id: "measurement",
        title: "Measured speedup in one workload",
        kind: "empirical_finding",
        role: "limitation",
        attribution: [],
        year: null,
      },
    ],
    relations: [
      {
        id: "inference",
        premises: ["hardware"],
        conclusion: "measurement",
        predicate: "premise_for",
      },
      {
        id: "reverse",
        premises: ["measurement"],
        conclusion: "hardware",
        predicate: "bounded_by",
      },
      {
        id: "proper",
        premises: ["hardware"],
        conclusion: "measurement",
        predicate: "bounded_by",
      },
    ],
  } as unknown as ReturnType<typeof validateDraft>;
  const checked = applyReview(
    {
      node_checks: [
        { id: "hardware", keep: true, assessed_role: "general_foundation" },
        { id: "measurement", keep: true, assessed_role: "limiting_condition" },
      ],
      relation_checks: draft.relations.map((r) => ({
        id: r.id,
        keep: true,
        direction_correct: true,
        scope_matches_endpoints: true,
        warrant_supported: true,
      })),
      gaps: [],
    },
    draft,
  );
  expect(checked.relations.map((r) => r.id)).toEqual(["proper"]);
  expect(checked.gaps.join(" ")).toContain("reported empirical observation");
  expect(checked.gaps.join(" ")).toContain("contradictory limiting arrow");
});
