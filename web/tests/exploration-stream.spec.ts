import { test, expect } from "@playwright/test";
import { createServer, type RequestListener } from "node:http";
import {
  EventDecoder,
  completedItems,
  completionStream,
  ProviderFailure,
} from "../src/explore/stream";
import { remainingEstimate, type Progress } from "../src/explore/progress";
import { Provider, modelOptions } from "../src/explore/provider";

const frame = (content: string) =>
  `data: ${JSON.stringify({ model: "fixture", choices: [{ delta: { content } }] })}\r\n\r\n`;
async function server<T>(
  handler: RequestListener,
  run: (url: string) => Promise<T>,
) {
  const instance = createServer(handler);
  await new Promise<void>((resolve) =>
    instance.listen(0, "127.0.0.1", resolve),
  );
  try {
    return await run(
      `http://127.0.0.1:${(instance.address() as { port: number }).port}`,
    );
  } finally {
    instance.closeAllConnections();
    await new Promise<void>((resolve) => instance.close(() => resolve()));
  }
}
function options(url: string) {
  return {
    url,
    init: {},
    model: "fixture",
    signal: new AbortController().signal,
    update: () => {},
    usage: () => {},
    limits: { firstMs: 150, idleMs: 150, totalMs: 2000, bytes: 10000 },
  };
}

test("SSE framing handles fragmented CRLF, multiline data and completion", () => {
  const values: string[] = [];
  const parser = new EventDecoder((v) => values.push(v));
  const stream =
    ": heartbeat\r\ndata: first\r\ndata: second\r\n\r\ndata: [DONE]\n\n";
  for (const char of stream) parser.push(char);
  parser.push("", true);
  expect(values).toEqual(["first\nsecond", "[DONE]"]);
  expect(
    completedItems(
      '{"nodes":[{"id":"n1","claim":"braces } and [ in a string"},{"id":"unfinished"',
      "nodes",
    ),
  ).toEqual([{ id: "n1", claim: "braces } and [ in a string" }]);
});

test("a completed response never waits indefinitely for transport cleanup", async () => {
  const originalFetch = globalThis.fetch;
  let cancelled = false;
  globalThis.fetch = async () =>
    new Response(
      new ReadableStream({
        start(controller) {
          controller.enqueue(
            new TextEncoder().encode(frame('{"ok":true}') + "data: [DONE]\n\n"),
          );
        },
        cancel() {
          cancelled = true;
          return new Promise<void>(() => {});
        },
      }),
      { headers: { "Content-Type": "text/event-stream" } },
    );
  try {
    const result = await Promise.race([
      completionStream(options("https://provider.invalid/test")),
      new Promise<never>((_resolve, reject) =>
        setTimeout(() => reject(new Error("cleanup stalled")), 500),
      ),
    ]);
    expect(result.content).toBe('{"ok":true}');
    expect(cancelled).toBe(true);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("healthy streamed activity continues past the first-response deadline and retains usage", async () => {
  const updates: string[] = [],
    usage: unknown[] = [];
  const result = await server(
    (_req, res) => {
      res.writeHead(200, { "Content-Type": "text/event-stream" });
      res.write(frame("α"));
      let sent = 0;
      const timer = setInterval(() => {
        res.write(frame("β"));
        if (++sent === 6) {
          clearInterval(timer);
          res.end(
            `data: ${JSON.stringify({ model: "fixture", choices: [{ delta: {}, finish_reason: "stop" }], usage: { prompt_tokens: 7, completion_tokens: 9 } })}\n\ndata: [DONE]\n\n`,
          );
        }
      }, 45);
      res.on("close", () => clearInterval(timer));
    },
    (url) =>
      completionStream({
        ...options(url),
        update: (v) => updates.push(v.content),
        usage: (a, b) => usage.push([a, b]),
      }),
  );
  expect(result.content).toBe("αββββββ");
  expect(result.elapsedMs).toBeGreaterThan(150);
  expect(result.firstContentMs).toBeLessThan(150);
  expect(updates.at(-1)).toBe(result.content);
  expect(usage).toEqual([[7, 9]]);
});

test("continuous formatting whitespace cannot keep a stalled model request alive", async () => {
  const start = Date.now();
  await server(
    (_req, res) => {
      res.writeHead(200, { "Content-Type": "text/event-stream" });
      res.write(frame('{"result":['));
      const timer = setInterval(() => res.write(frame(" \n ")), 20);
      res.on("close", () => clearInterval(timer));
    },
    async (url) => {
      await expect(completionStream(options(url))).rejects.toThrow(
        "stopped sending",
      );
    },
  );
  expect(Date.now() - start).toBeLessThan(1000);
});

test("interrupted streams expose completed content but never silently complete", async () => {
  let received = "";
  await expect(
    server(
      (_req, res) => {
        res.writeHead(200, { "Content-Type": "text/event-stream" });
        res.end(frame('{"nodes":[{"id":"n1"}],'));
      },
      (url) =>
        completionStream({
          ...options(url),
          update: (v) => {
            received = v.content;
          },
        }),
    ),
  ).rejects.toThrow("stream ended before completion");
  expect(completedItems(received, "nodes")).toEqual([{ id: "n1" }]);
});

test("first-content and stalled-stream timeouts are recoverable", async () => {
  await expect(
    server(
      (_req, res) => {
        res.writeHead(200, { "Content-Type": "text/event-stream" });
        res.flushHeaders();
      },
      (url) =>
        completionStream({
          ...options(url),
          limits: { firstMs: 60, idleMs: 60, totalMs: 1000, bytes: 10000 },
        }),
    ),
  ).rejects.toThrow("has not started");
  await expect(
    server(
      (_req, res) => {
        res.writeHead(200, { "Content-Type": "text/event-stream" });
        res.write(frame("partial"));
      },
      (url) =>
        completionStream({
          ...options(url),
          limits: { firstMs: 150, idleMs: 60, totalMs: 1000, bytes: 10000 },
        }),
    ),
  ).rejects.toThrow("stopped sending data");
});

test("provider error bodies and alternate models are never accepted", async () => {
  const failures: unknown[] = [];
  await server(
    (_req, res) => {
      res.writeHead(401);
      res.end("private-key-must-not-appear");
    },
    async (url) => {
      try {
        await completionStream(options(url));
      } catch (e) {
        failures.push(e);
      }
    },
  );
  expect(String(failures[0])).not.toContain("private-key-must-not-appear");
  expect((failures[0] as ProviderFailure).recoverable).toBe(false);
  await expect(
    server(
      (_req, res) => {
        res.writeHead(200, { "Content-Type": "text/event-stream" });
        res.end('data: {"model":"another-model","choices":[]}\n\n');
      },
      (url) => completionStream(options(url)),
    ),
  ).rejects.toThrow("different model");
});

test("remaining-time estimates become uncertain instead of counting down forever", () => {
  const p: Progress = {
    stage: 3,
    stageStarted: 1000,
    detail: "",
    papers: 1,
    passages: 1,
    atlas: 0,
    insights: 0,
    connections: 0,
    characters: 0,
    activity: [],
    titles: [],
    state: "working",
  };
  expect(remainingEstimate(p, 11000)).toContain("remaining");
  expect(remainingEstimate(p, 200000)).toContain("uncertain");
  expect(remainingEstimate({ ...p, state: "complete" }, 200000)).toBe("");
  expect(remainingEstimate({ ...p, stage: 4, deadline: 61000 }, 41000)).toBe(
    "Evidence check ends within 20 sec",
  );
  expect(
    remainingEstimate({ ...p, stage: 4, deadline: 61000 }, 200000),
  ).not.toContain("uncertain");
});

test("all models use a consistent bounded reasoning policy without contradictory options; repair shares its deadline", async () => {
  expect(modelOptions("deepseek-ai/DeepSeek-V4.1-Flash")).toEqual({
    enable_thinking: true,
    thinking_budget: 512,
  });
  expect(
    modelOptions("unlisted/reasoning-model", "evidence challenge"),
  ).toEqual({ enable_thinking: true, thinking_budget: 512 });
  expect(
    modelOptions("unlisted/reasoning-model", "relation check teaching r1"),
  ).toEqual({ enable_thinking: true, thinking_budget: 512 });
  expect(modelOptions("unlisted/reasoning-model", "draft graph")).toEqual({
    enable_thinking: true,
    thinking_budget: 1024,
  });
  expect(modelOptions("unlisted/reasoning-model", "connect insights")).toEqual({
    enable_thinking: true,
    thinking_budget: 1024,
  });
  const originalFetch = globalThis.fetch;
  const bodies: Record<string, unknown>[] = [];
  let calls = 0;
  await server(
    (req, res) => {
      let body = "";
      req.on("data", (chunk) => {
        body += chunk;
      });
      req.on("end", () => {
        bodies.push(JSON.parse(body));
        if (++calls === 1) {
          res.writeHead(200, { "Content-Type": "application/json" });
          return res.end(
            JSON.stringify({
              model: "deepseek-ai/DeepSeek-V4.1-Flash",
              choices: [
                {
                  message: { content: "{invalid JSON" },
                  finish_reason: "stop",
                },
              ],
            }),
          );
        }
        res.writeHead(200, { "Content-Type": "text/event-stream" });
        // A provider that ignores the thinking flag still cannot extend the hard deadline.
        const timer = setInterval(
          () =>
            res.write(
              `data: ${JSON.stringify({ model: "deepseek-ai/DeepSeek-V4.1-Flash", choices: [{ delta: { reasoning_content: "private reasoning fixture" } }] })}\n\n`,
            ),
          15,
        );
        res.on("close", () => clearInterval(timer));
      });
    },
    async (url) => {
      globalThis.fetch = (_url, init) => originalFetch(url, init);
      const provider = new Provider(
        "fixture-key",
        "deepseek-ai/DeepSeek-V4.1-Flash",
        new AbortController().signal,
      );
      const started = Date.now();
      try {
        await expect(
          provider.json(
            "evidence challenge",
            "JSON only",
            {},
            700,
            started + 250,
          ),
        ).rejects.toThrow("second limit");
        expect(Date.now() - started).toBeLessThan(1500);
        expect(calls).toBe(2);
        expect(bodies.map((b) => b.enable_thinking)).toEqual([true, true]);
        expect(bodies[0].thinking_budget).toBe(512);
        expect(bodies[1].thinking_budget).toBe(128);
        // A backend that counts reasoning inside max_tokens still has 700 answer tokens.
        expect(bodies.every((b) => b.max_tokens === 700 + 1024)).toBe(true);
        expect(provider.receipts[1].reasoning_characters).toBeGreaterThan(0);
        expect(provider.receipts[1].first_content_ms).toBeNull();
        expect(provider.receipts[1].outcome).toBe("failed");
        expect(JSON.stringify(provider.receipts)).not.toContain(
          "private reasoning fixture",
        );
        expect(JSON.stringify(provider.receipts)).not.toContain("fixture-key");
      } finally {
        provider.clear();
        globalThis.fetch = originalFetch;
      }
    },
  );
});

test("valid JSON with no requested record arrays is a bounded format failure, not an empty graph", async () => {
  const originalFetch = globalThis.fetch;
  let calls = 0;
  globalThis.fetch = async (_url, init) => {
    const body = JSON.parse(String(init?.body));
    const repairing = ++calls === 2;
    if (repairing) {
      const input = JSON.parse(body.messages[1].content);
      expect(input.expected_shape.properties.relations.type).toBe("array");
      expect(body.messages[0].content).toContain("never add claims");
    }
    return new Response(
      JSON.stringify({
        model: "fixture/format-shape",
        choices: [
          {
            message: {
              content: JSON.stringify(
                repairing
                  ? {
                      relations: [],
                      gaps: ["No connection records could be recovered."],
                    }
                  : {
                      commentary:
                        "Reasoning prose without the requested connections.",
                    },
              ),
            },
            finish_reason: "stop",
          },
        ],
        usage: { prompt_tokens: 12, completion_tokens: 18 },
      }),
      { headers: { "Content-Type": "application/json" } },
    );
  };
  const provider = new Provider(
    "fixture-key",
    "fixture/format-shape",
    new AbortController().signal,
  );
  try {
    expect(await provider.json("connect insights", "Fixture", {}, 100)).toEqual(
      {
        relations: [],
        gaps: ["No connection records could be recovered."],
      },
    );
    expect(provider.receipts.map((r) => r.outcome)).toEqual([
      "failed",
      "completed",
    ]);
    expect(provider.receipts.every((r) => r.input_tokens === 12)).toBe(true);
    await expect(
      provider.json("connect insights", "Fixture", {}, 100),
    ).rejects.toThrow("Record-format repair failed");
    expect(calls).toBe(4);
    expect(provider.receipts.at(-1)?.outcome).toBe("failed");
    // Explicit resume inherits the same two-repair ceiling.
    const resumed = new Provider(
      "fixture-key",
      "fixture/format-shape",
      new AbortController().signal,
      undefined,
      provider.receipts,
    );
    await expect(
      resumed.json("connect insights", "Fixture", {}, 100),
    ).rejects.toThrow("unusable record format");
    expect(calls).toBe(5);
  } finally {
    provider.clear();
    globalThis.fetch = originalFetch;
  }
});

test("unlisted models adapt only to explicit optional-field rejections and remember capabilities for this tab", async () => {
  const originalFetch = globalThis.fetch;
  const bodies: Record<string, unknown>[] = [];
  await server(
    (req, res) => {
      let body = "";
      req.on("data", (chunk) => {
        body += chunk;
      });
      req.on("end", () => {
        bodies.push(JSON.parse(body));
        if (bodies.length <= 2) {
          res.writeHead(400, { "Content-Type": "application/json" });
          return res.end(
            JSON.stringify({
              error: {
                message: `${bodies.length === 1 ? "response_format json_schema" : "enable_thinking thinking_budget"} is not supported. private-error-fixture`,
              },
            }),
          );
        }
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(
          JSON.stringify({
            model: "fixture/capability-test",
            choices: [
              {
                message: { content: '{"queries":[],"gaps":[]}' },
                finish_reason: "stop",
              },
            ],
            usage: { prompt_tokens: 10, completion_tokens: 8 },
          }),
        );
      });
    },
    async (url) => {
      globalThis.fetch = (_url, init) => originalFetch(url, init);
      try {
        const p = new Provider(
          "fixture-key",
          "fixture/capability-test",
          new AbortController().signal,
        );
        expect(await p.json("research plan", "JSON only", {}, 100)).toEqual({
          queries: [],
          gaps: [],
        });
        expect(p.receipts.map((r) => r.outcome)).toEqual([
          "failed",
          "failed",
          "completed",
        ]);
        expect(
          p.receipts
            .slice(0, 2)
            .every((r) => r.input_tokens === null && r.output_tokens === null),
        ).toBe(true);
        expect(JSON.stringify(p.receipts)).not.toContain(
          "private-error-fixture",
        );
        expect(bodies[0].response_format).toEqual({ type: "json_object" });
        expect(bodies[0].thinking_budget).toBe(512);
        expect(bodies[1].response_format).toBeUndefined();
        expect(bodies[1].enable_thinking).toBe(true);
        expect(bodies[2].enable_thinking).toBeUndefined();
        expect(bodies[2].thinking_budget).toBeUndefined();
        expect(bodies.every((b) => b.model === "fixture/capability-test")).toBe(
          true,
        );
        p.clear();
        const next = new Provider(
          "fixture-key",
          "fixture/capability-test",
          new AbortController().signal,
        );
        await next.json("research plan", "JSON only", {}, 100);
        expect(next.receipts).toHaveLength(1);
        expect(bodies[3].response_format).toBeUndefined();
        expect(bodies[3].enable_thinking).toBeUndefined();
        next.clear();
      } finally {
        globalThis.fetch = originalFetch;
      }
    },
  );
});

test("a rate-limit response is never retried or treated as a capability rejection", async () => {
  const originalFetch = globalThis.fetch;
  let calls = 0;
  await server(
    (_req, res) => {
      calls++;
      res.writeHead(429, { "Content-Type": "application/json" });
      res.end(
        '{"error":{"message":"response_format not supported: private-fixture"}}',
      );
    },
    async (url) => {
      globalThis.fetch = (_url, init) => originalFetch(url, init);
      const provider = new Provider(
        "fixture-key",
        "fixture/rate-limit",
        new AbortController().signal,
      );
      try {
        await expect(
          provider.json("research plan", "JSON only", {}, 100),
        ).rejects.toThrow("HTTP 429");
        expect(calls).toBe(1);
        expect(provider.receipts).toHaveLength(1);
        expect(provider.receipts[0].input_tokens).toBeNull();
      } finally {
        provider.clear();
        globalThis.fetch = originalFetch;
      }
    },
  );
});

test("valid token streams may exceed 2 MB in metadata while the answer stays small", async () => {
  const answer = JSON.stringify({
    explanation: "An inspectable research insight. ".repeat(1000),
  });
  const frames = [];
  for (let i = 0; i < answer.length; i += 6)
    frames.push(
      `data: ${JSON.stringify({
        id: "chatcmpl-0123456789abcdef0123456789abcdef",
        object: "chat.completion.chunk",
        created: 1792150000,
        model: "fixture",
        system_fingerprint: "fp_fixture_representative_metadata",
        choices: [
          {
            index: 0,
            delta: {
              role: "assistant",
              content: answer.slice(i, i + 6),
              reasoning_content: null,
            },
            logprobs: null,
            finish_reason: null,
          },
        ],
        usage: {
          prompt_tokens: 12000,
          completion_tokens: Math.floor(i / 6),
          total_tokens: 12000 + Math.floor(i / 6),
          prompt_tokens_details: { cached_tokens: 10000 },
        },
      })}\n\n`,
    );
  const body = frames.join("") + "data: [DONE]\n\n";
  expect(Buffer.byteLength(body)).toBeGreaterThan(2_000_000);
  expect(answer.length).toBeLessThan(100_000);
  const serve: RequestListener = (_req, res) => {
    res.writeHead(200, { "Content-Type": "text/event-stream" });
    res.end(body);
  };
  // Reproduce the former limit against exactly the same valid stream.
  await expect(
    server(serve, (url) =>
      completionStream({
        ...options(url),
        limits: {
          firstMs: 5000,
          idleMs: 5000,
          totalMs: 10000,
          bytes: 2_000_000,
        },
      }),
    ),
  ).rejects.toThrow("transfer limit");
  let measured = 0;
  const result = await server(serve, (url) =>
    completionStream({
      ...options(url),
      limits: undefined,
      update: (value) => {
        measured = value.transportBytes;
      },
    }),
  );
  expect(result.content).toBe(answer);
  expect(measured).toBe(Buffer.byteLength(body));
});

test("stream metadata and actual answer sizes remain independently bounded", async () => {
  expect(() =>
    new EventDecoder(() => {}).push("data: " + "x".repeat(262_145)),
  ).toThrow("oversized stream event");
  await expect(
    server(
      (_req, res) => {
        res.writeHead(200, { "Content-Type": "text/event-stream" });
        res.end(frame("x".repeat(100_001)) + "data: [DONE]\n\n");
      },
      (url) => completionStream({ ...options(url), limits: undefined }),
    ),
  ).rejects.toThrow("model response exceeded");
});

test("source packets preserve atlas foundations and earlier evidence within the same budget", async () => {
  const { packet } = await import("../src/explore/agent");
  const { localMatches } = await import("../src/explore/sources");
  const recent = Array.from({ length: 24 }, (_, i) => ({
    id: `s${i}`,
    title: "Transformer attention applications",
    authors: [],
    year: 2025,
    kind: "abstract" as const,
    passage: "evidence ".repeat(500),
    url: "https://doi.org/10.1234/test",
    retrieved_at: "fixture",
  }));
  const foundation = {
    ...recent[0],
    id: "foundation",
    title: "Soft alignment for translation",
    kind: "atlas" as const,
    year: 2015,
  };
  const earlier = {
    ...recent[0],
    id: "early",
    title: "Earlier attention mechanism",
    year: 2014,
  };
  const selected = packet(
    [...recent, foundation, earlier],
    "Transformer attention",
  );
  expect(selected.some((s) => s.id === "foundation" && s.excerpts.length)).toBe(
    true,
  );
  expect(selected.some((s) => s.id === "early" && s.excerpts.length)).toBe(
    true,
  );
  const crowdedAtlas = recent.map((s) => ({
    ...s,
    kind: "atlas" as const,
    year: 2017,
  }));
  expect(
    packet([...crowdedAtlas, foundation], "Transformer attention").some(
      (s) => s.id === "foundation" && s.excerpts.length,
    ),
  ).toBe(true);
  expect(
    selected.reduce(
      (n, s) => n + s.excerpts.reduce((sum, e) => sum + e.quote.length, 0),
      0,
    ),
  ).toBeLessThanOrEqual(36000);
  expect(
    localMatches(
      {
        release_id: "fixture",
        snapshot_hash: "a",
        total: 1,
        entries: [
          {
            id: "n",
            revision: 1,
            content_hash: "a",
            title: "Soft alignment",
            pillar: "computer_science",
            kind: "method",
            claim: "Learning alignment",
            explanation: "A learned alignment mechanism",
            assumptions: [],
            limits: [],
            date: {
              year: 2015,
              precision: "year",
              event: "publication",
              note: "",
            },
            attribution: [
              {
                name: "Dzmitry Bahdanau",
                role: "author",
                evidence_note: "fixture",
              },
            ],
          },
        ],
      },
      "Bahdanau",
    ),
  ).toHaveLength(1);
});

test("research matching ignores question words, substring coincidences and weak broad-query overlaps", async () => {
  const { localMatches } = await import("../src/explore/sources");
  const entry = {
    id: "irrelevant",
    revision: 1,
    content_hash: "a",
    title: "Experimental strain architecture",
    pillar: "physics",
    kind: "method",
    claim: "A candidate for a quantum spin effect",
    explanation: "A candidate material with a novel architecture.",
    assumptions: [],
    limits: [],
    date: { year: 2005, precision: "year", event: "publication", note: "" },
    attribution: [],
  };
  const index = {
    release_id: "fixture",
    snapshot_hash: "a",
    total: 2,
    entries: [
      entry,
      {
        ...entry,
        id: "relevant",
        title: "Transformer attention architecture",
        claim: "Attention models sequences",
        explanation: "Attention replaces recurrent computation.",
        date: { ...entry.date, year: 2017 },
      },
    ],
  };
  expect(
    localMatches(
      index,
      "How did the Transformer architecture build on earlier attention mechanisms?",
    ).map((s) => s.atlas_id),
  ).toEqual(["relevant"]);
  index.entries = [
    {
      ...entry,
      title: "Cell plasma and chemical gradients",
      claim: "Plasma membranes maintain chemical gradients.",
      explanation: "Chemical gradients in cells support transport.",
    },
  ];
  expect(
    localMatches(index, "plasma enhanced chemical vapour decomposition"),
  ).toHaveLength(0);
});

test("parallel checks cannot overshoot the session request limit while hashing inputs", async () => {
  const original = globalThis.fetch;
  let sent = 0;
  globalThis.fetch = async () => {
    sent++;
    return new Response(
      JSON.stringify({
        model: "budget-fixture",
        choices: [{ finish_reason: "stop", message: { content: "{}" } }],
        usage: { prompt_tokens: 2, completion_tokens: 2 },
      }),
      { headers: { "Content-Type": "application/json" } },
    );
  };
  const previous = Array.from({ length: 23 }, () => ({
    stage: "fixture",
    model: "budget-fixture",
    started_at: "fixture",
    outcome: "completed" as const,
    input_hash: "",
    prompt_hash: "",
    input_tokens: 1,
    output_tokens: 1,
  }));
  try {
    const provider = new Provider(
      "fixture-key",
      "budget-fixture",
      new AbortController().signal,
      () => {},
      previous,
    );
    const results = await Promise.allSettled(
      Array.from({ length: 4 }, (_, i) =>
        provider.json("evidence outline", "Fixture", { i }, 10),
      ),
    );
    expect(sent).toBe(1);
    expect(provider.receipts).toHaveLength(24);
    expect(results.filter((r) => r.status === "fulfilled")).toHaveLength(1);
  } finally {
    globalThis.fetch = original;
  }
});
