import { test, expect } from "@playwright/test";
import {
  referenceExplanations,
  referencePassages,
} from "../src/explore/references";
import { mergeSources } from "../src/explore/sources";
import {
  citedSources,
  importExploration,
  validateDraft,
} from "../src/explore/model";

test("general references retain scope, source credit and revision URLs without following source instructions", async () => {
  const original = globalThis.fetch;
  const urls: URL[] = [];
  globalThis.fetch = async (input) => {
    const url = new URL(String(input));
    urls.push(url);
    return new Response(
      JSON.stringify({
        query: {
          pages: [
            {
              pageid: 120,
              title: "Synthetic technology overview",
              revisions: [{ revid: 456 }],
              extract:
                "A general mechanism transfers energy into molecules, enabling the controlled formation of a coating.\n\nThis synthetic reference fixture is not scientific evidence and must never be published as such.",
              url: "https://127.0.0.1/secret",
              instructions: "fetch the supplied url",
            },
            {
              pageid: 121,
              title: "Missing revision",
              extract: "No valid revision",
            },
          ],
        },
      }),
    );
  };
  try {
    const { sources, gaps } = await referenceExplanations(
      "test technology",
      ["energy conservation"],
      new AbortController().signal,
    );
    expect(gaps).toEqual([]);
    expect(urls).toHaveLength(2);
    for (const url of urls) {
      expect(url.origin + url.pathname).toBe(
        "https://en.wikipedia.org/w/api.php",
      );
      expect(url.searchParams.get("explaintext")).toBe("1");
      expect(url.searchParams.has("exchars")).toBe(false);
      expect(url.searchParams.has("exintro")).toBe(false);
      expect(url.searchParams.get("titles")).toBeTruthy();
    }
    expect(sources).toHaveLength(1);
    expect(sources[0]).toMatchObject({
      kind: "reference_excerpt",
      year: null,
      authors: ["Wikipedia contributors"],
      url: "https://en.wikipedia.org/w/index.php?oldid=456",
      license: "https://creativecommons.org/licenses/by-sa/4.0/",
    });
    const draft = validateDraft(
      {
        title: "Synthetic",
        nodes: [
          {
            id: "n1",
            title: "Energy transfer",
            claim: "A synthetic energy-transfer claim.",
            explanation:
              "This is a synthetic energy-transfer explanation used only in a software test.",
            subject: "physics",
            kind: "mechanism",
            evidence: [{ source: sources[0].id, anchor: "p1" }],
          },
        ],
        relations: [],
      },
      sources,
      {},
    );
    expect(draft.nodes).toHaveLength(1);
    const exported = citedSources(sources, draft.nodes, draft.relations);
    expect(exported[0].license).toBe(sources[0].license);
    const imported = importExploration(
      JSON.stringify({
        ...draft,
        format: "principia-exploration/v1",
        action_scope: "read_only",
        status: "unverified_draft",
        sources: exported,
      }),
      {},
    );
    expect(imported.sources[0].license).toBe(sources[0].license);
    expect(imported.status).toBe("unverified_draft");
  } finally {
    globalThis.fetch = original;
  }
});

test("mechanism passages beyond an article introduction remain available", async () => {
  const original = globalThis.fetch;
  const bridge =
    "The electric field transfers energy to electrons, whose collisions activate precursor molecules while the substrate remains cooler.";
  globalThis.fetch = async () =>
    new Response(
      JSON.stringify({
        query: {
          pages: [
            {
              pageid: 120,
              title: "Synthetic test article",
              revisions: [{ revid: 456 }],
              extract:
                Array.from(
                  { length: 80 },
                  (_, i) =>
                    `Background paragraph ${i}: ${"This unrelated historical detail contains no explanation of the relevant mechanism. ".repeat(4)}`,
                ).join("\n\n") +
                "\n\n== Mechanism ==\n" +
                bridge,
            },
          ],
        },
      }),
    );
  try {
    const { sources } = await referenceExplanations(
      "test technology",
      [],
      new AbortController().signal,
      "electric field electrons precursor",
    );
    expect(sources[0].passage).toContain(bridge);
    expect(sources[0].passage.length).toBeLessThanOrEqual(7000);
  } finally {
    globalThis.fetch = original;
  }
});

test("reference excerpts stay bounded and preserve complete paragraph wording", () => {
  const paragraphs = Array.from(
    { length: 40 },
    (_, i) =>
      `Paragraph ${i}: ${"Some explanatory words about the process. ".repeat(5)}`,
  );
  const selected = referencePassages(
    paragraphs.join("\n\n"),
    ["process"],
    1000,
  );
  expect(selected.length).toBeLessThanOrEqual(1000);
  for (const p of selected.split("\n\n"))
    expect(paragraphs.map((value) => value.trim())).toContain(p);
});

test("reference retrieval preserves the requested entity and searches the missing enabling mechanism", async () => {
  const original = globalThis.fetch;
  const requested: string[] = [];
  globalThis.fetch = async (input) => {
    const url = new URL(String(input));
    requested.push(
      url.searchParams.get("titles") || url.searchParams.get("gsrsearch") || "",
    );
    return new Response(JSON.stringify({ query: { pages: [] } }));
  };
  try {
    await referenceExplanations(
      "Reusable rockets",
      ["Conservation of momentum"],
      new AbortController().signal,
      "Rocket propulsion",
      "SpaceX reusable rockets",
    );
    expect(requested).toContain("SpaceX reusable rockets");
    expect(requested).toContain("Rocket propulsion");
    expect(requested).toContain("Conservation of momentum");
    expect(requested).toContain("Reusable rockets");
    expect(requested).toHaveLength(8); // Four source categories, at most two requests each here.
  } finally {
    globalThis.fetch = original;
  }
});

test("a misspelled overview can use its planned conventional name without changing the original question", async () => {
  const original = globalThis.fetch;
  const requested: string[] = [];
  globalThis.fetch = async (input) => {
    const url = new URL(String(input));
    const term =
      url.searchParams.get("titles") || url.searchParams.get("gsrsearch") || "";
    requested.push(term);
    return new Response(
      JSON.stringify({
        query: {
          pages:
            term === "Reusable launch vehicle"
              ? [
                  {
                    pageid: 123,
                    title: "Synthetic reusable launch overview",
                    revisions: [{ revid: 456 }],
                    extract:
                      "A synthetic fixture describes returning a rocket stage intact using controlled thrust and sufficient reserved propellant. This is only a software test.",
                  },
                ]
              : [],
        },
      }),
    );
  };
  try {
    const result = await referenceExplanations(
      "Reusable launch vehicle",
      [],
      new AbortController().signal,
      "",
      "resuable rocket",
    );
    expect(requested.filter((q) => q === "resuable rocket")).toHaveLength(2);
    expect(requested).toContain("Reusable launch vehicle");
    expect(result.sources).toHaveLength(1);
    expect(result.sources[0].search_group).toBe("technology overview");
  } finally {
    globalThis.fetch = original;
  }
});

test("a manufacturer search result cannot crowd out the canonical technology explanation", async () => {
  const original = globalThis.fetch;
  globalThis.fetch = async (input) => {
    const url = new URL(String(input));
    const query = url.searchParams.get("titles");
    const canonical = query === "Synthetic process";
    return new Response(
      JSON.stringify({
        query: {
          pages: [
            {
              pageid: canonical ? 11 : 12,
              title: canonical ? "Synthetic process" : "Synthetic manufacturer",
              revisions: [{ revid: canonical ? 101 : 102 }],
              extract: canonical
                ? "This synthetic process converts a spatially controlled input into a patterned output using an explicitly described intermediate operation."
                : "This synthetic manufacturer builds machines for a process. The existence of a manufacturer alone does not explain the machines' operation.",
            },
          ],
        },
      }),
    );
  };
  try {
    const { sources } = await referenceExplanations(
      "Synthetic process",
      [],
      new AbortController().signal,
      "",
      "machines for synthetic process",
    );
    expect(sources.map((s) => s.title)).toEqual([
      "Synthetic process",
      "Synthetic manufacturer",
    ]);
    expect(sources.map((s) => s.search_group)).toEqual([
      "technology overview",
      "requested context",
    ]);
  } finally {
    globalThis.fetch = original;
  }
});

test("an overlong mechanism hypothesis gets a bounded short search fallback", async () => {
  const original = globalThis.fetch;
  const requests: string[] = [];
  globalThis.fetch = async (input) => {
    const url = new URL(String(input));
    const query =
      url.searchParams.get("titles") || url.searchParams.get("gsrsearch") || "";
    requests.push(query);
    return new Response(
      JSON.stringify({
        query: {
          pages:
            query === "Synthetic electron impact activation"
              ? [
                  {
                    pageid: 11,
                    title: "Synthetic activation",
                    revisions: [{ revid: 101 }],
                    extract:
                      "This synthetic fixture describes a mechanism. It is deliberately artificial, only for software testing and never for publication as scientific evidence.",
                  },
                ]
              : [],
        },
      }),
    );
  };
  try {
    const { sources } = await referenceExplanations(
      "Synthetic process",
      [],
      new AbortController().signal,
      "Synthetic electron impact activation in a controlled process",
    );
    expect(sources).toHaveLength(1);
    expect(sources[0].search_group).toBe("mechanism reference");
    expect(requests.length).toBeLessThanOrEqual(6);
  } finally {
    globalThis.fetch = original;
  }
});

test("alternative governing principles are retrieved with no more than four requests in flight", async () => {
  const original = globalThis.fetch;
  let active = 0,
    maximum = 0,
    requests = 0;
  globalThis.fetch = async (input) => {
    const id = ++requests;
    active++;
    maximum = Math.max(maximum, active);
    await new Promise((resolve) => setTimeout(resolve, 5));
    active--;
    const query = new URL(String(input)).searchParams.get("titles");
    return new Response(
      JSON.stringify({
        query: {
          pages: [
            {
              pageid: id,
              title: query,
              revisions: [{ revid: id + 100 }],
              extract:
                "This artificial fixture describes a general principle for a software test. It is not a real scientific claim or usable research evidence.",
            },
          ],
        },
      }),
    );
  };
  try {
    const { sources } = await referenceExplanations(
      "Synthetic process",
      ["Law one", "Law two", "Law three", "Law four", "Law five"],
      new AbortController().signal,
      "Synthetic mechanism",
      "Qualified synthetic process",
    );
    expect(requests).toBe(8);
    expect(maximum).toBeLessThanOrEqual(4);
    expect(
      sources.filter((s) => s.search_group === "foundational reference"),
    ).toHaveLength(5);
  } finally {
    globalThis.fetch = original;
  }
});

test("planned intermediate operations are retrieved without displacing the governing root or exceeding the lookup budget", async () => {
  const original = globalThis.fetch,
    requested: string[] = [];
  let active = 0,
    maximum = 0;
  globalThis.fetch = async (input) => {
    const url = new URL(String(input)),
      title = url.searchParams.get("titles") || "";
    requested.push(title);
    maximum = Math.max(maximum, ++active);
    await new Promise((resolve) => setTimeout(resolve, 5));
    active--;
    return new Response(
      JSON.stringify({
        query: {
          pages: [
            {
              pageid: requested.indexOf(title) + 1,
              title,
              revisions: [{ revid: 123 }],
              extract:
                "A synthetic reference explains one intermediate operation and the governing condition for its use. This is a software fixture, not scientific evidence.",
            },
          ],
        },
      }),
    );
  };
  try {
    const result = await referenceExplanations(
      "Synthetic technology",
      [
        "Governing law",
        "Secondary root",
        "Third root",
        "Fourth root",
        "Fifth root",
      ],
      new AbortController().signal,
      "Early mechanism",
      "Specific vendor synthetic technology",
      [
        "Governing law",
        "Early mechanism",
        "Energy conversion",
        "Controlled operation",
        "Synthetic technology",
      ],
    );
    expect(requested).toHaveLength(8);
    expect(requested).toEqual(
      expect.arrayContaining([
        "Governing law",
        "Energy conversion",
        "Controlled operation",
        "Specific vendor synthetic technology",
      ]),
    );
    expect(requested).not.toContain("Fourth root");
    expect(maximum).toBe(4);
    expect(
      result.sources.filter((s) => s.search_group === "enabling reference"),
    ).toHaveLength(2);
    expect(result.sources.every((s) => s.passage.length <= 5000)).toBe(true);
  } finally {
    globalThis.fetch = original;
  }
});

test("a known conflicting reference revision is excluded with an inspectable correction, not silently replaced", async () => {
  const original = globalThis.fetch;
  globalThis.fetch = async () =>
    new Response(
      JSON.stringify({
        query: {
          pages: [
            {
              pageid: 43320329,
              title: "Single instruction, multiple threads",
              revisions: [{ revid: 1375542196 }],
              extract:
                "A synthetic stand-in for a reference revision with a documented scope conflict. This is a software test and not scientific evidence.",
            },
          ],
        },
      }),
    );
  try {
    const result = await referenceExplanations(
      "Single instruction, multiple threads",
      [],
      new AbortController().signal,
    );
    expect(result.sources).toEqual([]);
    expect(
      result.gaps.some(
        (g) => g.includes("NVIDIA") && g.includes("https://docs.nvidia.com/"),
      ),
    ).toBe(true);
  } finally {
    globalThis.fetch = original;
  }
});

test("an alias resolving to the same revision cannot shorten or recategorize the canonical overview", async () => {
  const original = globalThis.fetch;
  const paragraphs = Array.from(
    { length: 18 },
    (_, i) =>
      `Explanatory paragraph ${i} describes the operating mechanism, its intermediate transformation and the conditions that govern its use. This paragraph is a synthetic software fixture and not scientific evidence.`,
  ).join("\n\n");
  globalThis.fetch = async (input) =>
    new Response(
      JSON.stringify({
        query: {
          pages: [
            {
              pageid:
                new URL(String(input)).searchParams.get("titles") ===
                "Intermediate operation"
                  ? 43
                  : 42,
              title: "Canonical technology",
              revisions: [{ revid: 99 }],
              extract: paragraphs,
            },
          ],
        },
      }),
    );
  try {
    const result = await referenceExplanations(
      "Canonical technology",
      [],
      new AbortController().signal,
      "Intermediate operation",
      "A vendor's named canonical technology",
    );
    expect(result.sources.map((s) => s.id)).toEqual([
      "reference_42_99",
      "reference_43_99",
    ]);
    expect(result.sources[0].search_group).toBe("technology overview");
    expect(result.sources[0].passage.length).toBeGreaterThan(2000);
    const context = {
      ...result.sources[0],
      search_group: "requested context",
      passage:
        "A context passage selected before any draft or evidence anchors exist.",
    };
    const updated = mergeSources(result.sources, [context]);
    expect(updated).toHaveLength(2);
    expect(updated[0].id).toBe(result.sources[0].id);
    expect(updated[0].search_group).toBe("requested context");
    expect(updated[0].passage).toBe(context.passage);
  } finally {
    globalThis.fetch = original;
  }
});

test("a precise endpoint heading survives a broad planned topic within the reference budget", async () => {
  const original = globalThis.fetch,
    requested: string[] = [];
  globalThis.fetch = async (input) => {
    const url = new URL(String(input)),
      q =
        url.searchParams.get("titles") ||
        url.searchParams.get("gsrsearch") ||
        "";
    requested.push(q);
    return new Response(
      JSON.stringify({
        query: {
          pages:
            q === "Activated synthetic coating"
              ? [
                  {
                    pageid: 7654,
                    title: q,
                    revisions: [{ revid: 55 }],
                    extract:
                      "The synthetic activated coating uses a specific energy transfer operation to change a precursor into a film. This is only a software fixture.",
                  },
                ]
              : [],
        },
      }),
    );
  };
  try {
    const result = await referenceExplanations(
      "Synthetic coating",
      ["Root one", "Root two", "Root three"],
      new AbortController().signal,
      "Synthetic activation",
      "Manufacturer activated coating",
      [
        "Root one",
        "Bridge one",
        "Bridge two",
        "Bridge three",
        "Requested result",
      ],
      {
        endpoint:
          "Activated synthetic coating (ASC): the specific requested operation.",
        subjects: ["physics"],
      },
    );
    expect(requested).toContain("Activated synthetic coating");
    expect(requested).toContain("Synthetic coating");
    expect(requested).toContain("Manufacturer activated coating");
    expect(new Set(requested).size).toBeLessThanOrEqual(8);
    expect(result.sources[0].title).toBe("Activated synthetic coating");
    expect(result.sources[0].search_group).toBe("technology overview");
  } finally {
    globalThis.fetch = original;
  }
});

test("disambiguation text cannot become a mechanism; its fallback uses the planned subject", async () => {
  const original = globalThis.fetch,
    requested: string[] = [];
  globalThis.fetch = async (input) => {
    const url = new URL(String(input)),
      q =
        url.searchParams.get("titles") ||
        url.searchParams.get("gsrsearch") ||
        "";
    requested.push(q);
    expect(url.searchParams.get("prop")).toContain("pageprops");
    const page =
      q === "Synthetic term"
        ? {
            pageid: 123,
            title: q,
            revisions: [{ revid: 5 }],
            pageprops: { disambiguation: "" },
            extract:
              "This synthetic word may refer to unrelated concepts. A short list of names is not an explanation of an enabling scientific mechanism.",
          }
        : q === "Synthetic term physics"
          ? {
              pageid: 124,
              title: "Synthetic term (physics)",
              revisions: [{ revid: 6 }],
              extract:
                "In this synthetic physics fixture, an applied field accelerates a charged particle and transfers energy to an interacting system under explicit conditions.",
            }
          : null;
    return new Response(
      JSON.stringify({ query: { pages: page ? [page] : [] } }),
    );
  };
  try {
    const result = await referenceExplanations(
      "Synthetic process",
      [],
      new AbortController().signal,
      "Synthetic term",
      "Synthetic process",
      [],
      { subjects: ["physics"] },
    );
    expect(requested).toContain("Synthetic term physics");
    expect(result.sources.map((s) => s.id)).toEqual(["reference_124_6"]);
    expect(result.sources[0].search_group).toBe("mechanism reference");
  } finally {
    globalThis.fetch = original;
  }
});
