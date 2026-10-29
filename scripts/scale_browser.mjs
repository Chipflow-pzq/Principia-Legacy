/** Synthetic compact-index acceptance. No records enter the scientific corpus. */
import { chromium } from "../web/node_modules/@playwright/test/index.mjs";
import { mkdir, readdir, writeFile } from "node:fs/promises";
import { execFileSync } from "node:child_process";

const base = process.env.PRINCIPIA_TEST_URL || "http://127.0.0.1:8768/";
if (!["127.0.0.1", "localhost"].includes(new URL(base).hostname))
  throw new Error("Synthetic acceptance must use a loopback preview.");
const worker = (await readdir("web_dist/assets")).find((x) =>
  /^search.worker-.*\.js$/.test(x),
);
if (!worker) throw new Error("Build the reader first.");
const results = [];
for (const size of [10000, 50000, 100000]) {
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  try {
    const page = await browser.newPage();
    const blocked = [];
    await page.route("**/*", async (route) => {
      const url = new URL(route.request().url());
      if (url.origin !== new URL(base).origin) {
        blocked.push(url.origin);
        return route.abort();
      }
      await route.continue();
    });
    await page.goto(base);
    await page.locator(".flagship-card").first().waitFor();
    const result = await page.evaluate(
      async ({ size, worker }) => {
        const subjects = [
          "mathematics",
          "physics",
          "computer_science",
          "economics",
          "biology_medicine",
        ];
        const entries = Array.from({ length: size }, (_, i) => ({
          id: `synthetic-${i}`,
          revision: 1,
          content_hash: "0".repeat(64),
          compact: true,
          title: `SYNTHETIC insight ${i} in family${i % 1000}`,
          kind: "method",
          pillar: subjects[i % 5],
          claim: `Synthetic mechanism family${i % 1000} and group${i % 37}; this is not scientific evidence.`,
          explanation: `Synthetic retrieval fixture. Controlled variation in fields tests bounded ranking, independent of scientific accuracy. Category${i % 101} and test${i % 73}.`,
          assumptions: [],
          limits: ["Synthetic load data"],
          attribution: [{ name: `Synthetic person ${i % 100}` }],
          date: { year: 1900 + (i % 125) },
          neighbors: [`synthetic-${(i + 1) % size}`],
        }));
        const started = performance.now();
        const engine = new Worker(`/assets/${worker}`, { type: "module" });
        let id = 0;
        const request = (message) =>
          new Promise((resolve, reject) => {
            const current = ++id;
            const timer = setTimeout(
              () => reject(new Error("Worker timeout")),
              60000,
            );
            const receive = (event) => {
              if (event.data.id !== current) return;
              clearTimeout(timer);
              engine.removeEventListener("message", receive);
              resolve(event.data);
            };
            engine.addEventListener("message", receive);
            engine.postMessage({ ...message, id: current });
          });
        await request({ type: "init", entries });
        const transferredMs = performance.now() - started;
        let tick = performance.now(),
          maxGap = 0;
        const heartbeat = setInterval(() => {
          const at = performance.now();
          maxGap = Math.max(maxGap, at - tick);
          tick = at;
        }, 16);
        const first = performance.now();
        const firstResult = await request({
          type: "rank",
          query: "family42",
          limit: 8,
          subjects: [],
        });
        const firstQueryMs = performance.now() - first;
        const times = [];
        for (let i = 0; i < 40; i++) {
          const start = performance.now();
          const found = await request({
            type: "rank",
            query: i % 2 ? `family${i}` : "synthetic",
            limit: 8,
            subjects: [],
          });
          times.push({
            query: i % 2 ? "distinct" : "broad",
            ms: performance.now() - start,
            results: found.ids.length,
          });
        }
        clearInterval(heartbeat);
        // Keep the live worker for process-memory measurement, then close the browser.
        window.__syntheticScaleWorker = engine;
        return {
          size,
          transferred_ms: transferredMs,
          first_query_ms: firstQueryMs,
          first_results: firstResult.ids.length,
          main_thread_max_timer_gap_ms: maxGap,
          samples: times,
          js_heap_bytes: performance.memory?.usedJSHeapSize ?? null,
        };
      },
      { size, worker },
    );
    const cdp = await browser.newBrowserCDPSession();
    const { processInfo } = await cdp.send("SystemInfo.getProcessInfo");
    const roots = new Set(
      processInfo.filter((p) => p.type === "browser").map((p) => p.id),
    );
    const processes = execFileSync("ps", ["-axo", "pid,ppid,rss"], {
      encoding: "utf8",
    })
      .trim()
      .split("\n")
      .slice(1)
      .map((line) => line.trim().split(/\s+/).map(Number));
    for (let changed = true; changed;) {
      changed = false;
      for (const [pid, parent] of processes)
        if (roots.has(parent) && !roots.has(pid)) {
          roots.add(pid);
          changed = true;
        }
    }
    result.browser_process_tree_rss_bytes = processes.reduce(
      (n, [pid, , rss]) => n + (roots.has(pid) ? rss * 1024 : 0),
      0,
    );
    result.blocked_external_origins = [...new Set(blocked)];
    result.warm_p95_ms = Object.fromEntries(
      ["distinct", "broad"].map((type) => {
        const times = result.samples
          .filter((s) => s.query === type)
          .map((s) => s.ms)
          .sort((a, b) => a - b);
        return [type, times[Math.ceil(times.length * 0.95) - 1]];
      }),
    );
    results.push(result);
    console.log(JSON.stringify({ ...result, samples: undefined }));
  } finally {
    await browser.close();
  }
}
await mkdir("reports", { recursive: true });
await writeFile(
  "reports/browser-scale-1.5.json",
  JSON.stringify(
    {
      at: new Date().toISOString(),
      synthetic_only: true,
      protocol:
        "Fresh Chrome per size; real bundled ranking worker; 20 distinct and 20 broad warm requests; OS browser process tree RSS includes reader page and worker, excludes backend.",
      results,
    },
    null,
    2,
  ),
);
