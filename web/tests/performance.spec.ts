import { test, expect } from "@playwright/test";
import { writeFileSync, mkdirSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../../", import.meta.url));

test("record first view and offline page network evidence", async ({
  page,
  browser,
}, testInfo) => {
  test.skip(
    testInfo.project.name !== "desktop",
    "Measure one desktop profile; mobile has separate UX tests.",
  );
  const requests: string[] = [];
  await page.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    requests.push(url.origin);
    if (url.hostname !== "127.0.0.1") return route.abort();
    await route.continue();
  });
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const start = Date.now();
  await page.goto("/");
  await expect(page.locator(".flagship-card")).toHaveCount(5);
  const firstView = Date.now() - start;
  await page.screenshot({
    path: resolve(root, "docs/screenshots/reader-home.png"),
  });
  await page
    .locator(".flagship-card")
    .filter({ hasText: "The Transformer and attention" })
    .click();
  await expect(page.getByRole("img")).toHaveAttribute(
    "aria-label",
    /[1-9][0-9]* contributions/,
  );
  await page.screenshot({
    path: resolve(root, "docs/screenshots/reader-map.png"),
  });
  const memory = await page.evaluate(
    () =>
      (performance as Performance & { memory?: { usedJSHeapSize: number } })
        .memory?.usedJSHeapSize ?? null,
  );
  const processes = execFileSync("ps", ["-axo", "pid,ppid,rss,command"], {
    encoding: "utf8",
  })
    .trim()
    .split("\n")
    .slice(1)
    .map((line) => {
      const match = line.trim().match(/^(\d+)\s+(\d+)\s+(\d+)\s+(.*)$/);
      return match
        ? {
            pid: +match[1],
            parent: +match[2],
            rss: +match[3] * 1024,
            command: match[4],
          }
        : null;
    })
    .filter((x) => x !== null);
  // Scope RSS to this test's own browser. Concurrent paid QA browsers must
  // not be silently counted as part of the reader's working set.
  const session = await browser.newBrowserCDPSession();
  const { processInfo } = await session.send("SystemInfo.getProcessInfo");
  await session.detach();
  const roots = new Set<number>(
    processInfo
      .filter((p: { type: string }) => p.type === "browser")
      .map((p: { id: number }) => p.id),
  );
  expect(roots.size).toBe(1);
  let grew = true;
  while (grew) {
    grew = false;
    for (const p of processes)
      if (roots.has(p.parent) && !roots.has(p.pid)) {
        roots.add(p.pid);
        grew = true;
      }
  }
  const browserRSS = processes
    .filter((p) => roots.has(p.pid))
    .reduce((s, p) => s + p.rss, 0);
  const serverPort = new URL(testInfo.project.use.baseURL!).port || "80";
  const serverPids = new Set(
    execFileSync("lsof", ["-tiTCP:" + serverPort, "-sTCP:LISTEN"], {
      encoding: "utf8",
    })
      .trim()
      .split(/\s+/)
      .map(Number),
  );
  const serverRSS = processes
    .filter((p) => serverPids.has(p.pid))
    .reduce((s, p) => s + p.rss, 0);
  const result = {
    first_view_ms: firstView,
    first_view_definition:
      "fresh automated Chrome page, bundled app loaded and five flagship controls visible",
    js_heap_bytes: memory,
    browser_process_rss_bytes: browserRSS,
    reader_process_rss_bytes: serverRSS,
    combined_rss_bytes: browserRSS + serverRSS,
    memory_method:
      "ps RSS summed over this browser's CDP-identified process tree plus the local reader; unrelated QA browsers excluded; shared pages may be counted more than once",
    requests: requests.length,
    external_requests: requests.filter(
      (x) => x !== new URL(testInfo.project.use.baseURL!).origin,
    ),
    page_errors: errors,
    viewport: { width: 1440, height: 1000 },
  };
  mkdirSync(resolve(root, "build"), { recursive: true });
  writeFileSync(
    resolve(root, "build/browser-performance.json"),
    JSON.stringify(result, null, 2) + "\n",
  );
  expect(result.external_requests).toEqual([]);
  expect(errors).toEqual([]);
  expect(firstView).toBeLessThan(5000);
});
