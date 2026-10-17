/** Opt-in paid acceptance test. Run from the repository root; output stays in ignored .work. */
import {
  chromium,
  expect,
} from "../web/node_modules/@playwright/test/index.mjs";
import ts from "../web/node_modules/typescript/lib/typescript.js";
import { readFile, writeFile, mkdir, unlink } from "node:fs/promises";
const protocol = JSON.parse(
  await readFile("web/tests/live-exploration.queries.json", "utf8"),
);
const models = process.argv.slice(2);
if (!models.length)
  throw new Error(
    "Pass one or more exact provider model IDs. This test submits paid requests.",
  );
const selected = protocol.queries.map((_, i) => i);
const tag = new Date().toISOString().replace(/[:.]/g, "-");
const baseURL = process.env.PRINCIPIA_TEST_URL || "http://127.0.0.1:8767/";
const location = new URL(baseURL);
if (
  location.protocol !== "http:" ||
  !["127.0.0.1", "localhost", "[::1]"].includes(location.hostname)
)
  throw new Error("This acceptance runner only targets a loopback preview.");
await mkdir(".work/live-browser", { recursive: true });
const resumeDir = process.env.PRINCIPIA_QA_RESUME_DIR;
if (resumeDir && !/^\.work\/live-browser\/[0-9TZ-]+$/.test(resumeDir))
  throw new Error("Resume only an existing timestamped local QA run.");
const dir = resumeDir || ".work/live-browser/" + tag;
if (!resumeDir) await mkdir(dir, { recursive: false });
const env = process.env.SILICONFLOW_ENV_FILE
  ? await readFile(process.env.SILICONFLOW_ENV_FILE, "utf8")
  : "";
const key =
  process.env.SILICONFLOW_API_KEY ||
  env
    .match(
      /^(?:export\s+)?SILICONFLOW_API_KEY\s*=\s*['"]?([^'"\r\n]+)['"]?$/m,
    )?.[1]
    ?.trim();
if (!key)
  throw new Error(
    "Set SILICONFLOW_ENV_FILE to an external credential file, or supply SILICONFLOW_API_KEY in the environment.",
  );
const lineageCode = ts.transpileModule(
  await readFile("web/src/explore/lineage.ts", "utf8"),
  {
    compilerOptions: {
      module: ts.ModuleKind.ESNext,
      target: ts.ScriptTarget.ES2022,
    },
  },
).outputText;
const { lineage } = await import(
  "data:text/javascript;base64," + Buffer.from(lineageCode).toString("base64")
);
const browser = await chromium.launch({ headless: true, channel: "chrome" });
const report = resumeDir
  ? JSON.parse(await readFile(dir + "/report.json", "utf8"))
  : {
      started_at: new Date().toISOString(),
      protocol,
      attempts: [],
      available_models: [],
      requested_models: models,
      base_url: baseURL,
      output_directory: dir,
    };
if (resumeDir) {
  if (
    report.base_url !== baseURL ||
    JSON.stringify(report.requested_models) !== JSON.stringify(models) ||
    JSON.stringify(report.protocol) !== JSON.stringify(protocol)
  )
    throw new Error(
      "The run's URL, model selection and protocol must match before resuming.",
    );
  if (report.attempts.some((a) => !a.finished_at))
    throw new Error(
      "An unfinished attempt needs inspection; it will not be silently resubmitted.",
    );
  report.resumptions ||= [];
  report.resumptions.push({
    at: new Date().toISOString(),
    after_attempts: report.attempts.length,
    previous_stop_reason: report.stop_reason,
  });
  delete report.finished_at;
  delete report.stop_reason;
  await unlink(dir + "/STOP").catch((error) => {
    if (error.code !== "ENOENT") throw error;
  });
}
const flush = () =>
  writeFile(dir + "/report.json", JSON.stringify(report, null, 2));
function responseContent(wire) {
  let content = "",
    usage = null;
  for (const line of wire.split("\n")) {
    if (!line.startsWith("data:")) continue;
    try {
      const j = JSON.parse(line.slice(5));
      usage = j.usage || usage;
      content += (j.choices || []).map((c) => c.delta?.content || "").join("");
    } catch {}
  }
  if (!content && wire.trim().startsWith("{"))
    try {
      const j = JSON.parse(wire);
      content = j.choices?.[0]?.message?.content || "";
      usage = j.usage || usage;
    } catch {}
  return { content, usage };
}
try {
  matrix: for (const model of models)
    for (const queryIndex of selected) {
      // Completed cases, including unfavorable outcomes, are never replayed by resume.
      if (
        report.attempts.some(
          (a) => a.model === model && a.query_index === queryIndex,
        )
      )
        continue;
      const stop = await readFile(dir + "/STOP", "utf8").catch(() => null);
      if (stop) {
        report.stop_reason = stop;
        break matrix;
      }
      const query = protocol.queries[queryIndex],
        caseId = report.attempts.length + 1;
      const context = await browser.newContext({
          viewport: { width: 1440, height: 1000 },
        }),
        page = await context.newPage();
      const a = {
        case: caseId,
        query_index: queryIndex,
        query,
        model,
        started_at: new Date().toISOString(),
        finished: false,
        first_insight_seconds: null,
        first_connection_seconds: null,
        errors: [],
        page_errors: [],
        progress: [],
        private_input_to_atlas: false,
        network_hosts: [],
        requests: [],
        receipts: [],
      };
      report.attempts.push(a);
      await flush();
      const captures = [];
      await page.addInitScript(() => {
        window.__qaResponses = [];
        const original = window.fetch.bind(window);
        window.fetch = async (...args) => {
          const response = await original(...args);
          if (String(args[0]).endsWith("/chat/completions") && response.ok) {
            const record = {
              request: JSON.parse(args[1].body),
              content: "",
              usage: null,
              finished: false,
            };
            window.__qaResponses.push(record);
            const reader = response.clone().body.getReader(),
              decoder = new TextDecoder();
            (async () => {
              let pending = "";
              try {
                while (true) {
                  const part = await reader.read();
                  if (part.done) break;
                  pending += decoder.decode(part.value, { stream: true });
                  let newline;
                  while ((newline = pending.indexOf("\n")) >= 0) {
                    const line = pending.slice(0, newline);
                    pending = pending.slice(newline + 1);
                    if (!line.startsWith("data:")) continue;
                    try {
                      const j = JSON.parse(line.slice(5));
                      record.content += (j.choices || [])
                        .map((c) => c.delta?.content || "")
                        .join("");
                      record.usage = j.usage || record.usage;
                    } catch {}
                  }
                }
              } catch {
              } finally {
                record.finished = true;
              }
            })();
          }
          return response;
        };
      });
      page.on("pageerror", (e) =>
        a.page_errors.push(e.message.replaceAll(key, "[redacted]")),
      );
      page.on("request", (r) => {
        const u = new URL(r.url());
        if (!a.network_hosts.includes(u.hostname))
          a.network_hosts.push(u.hostname);
        if (
          u.hostname === "127.0.0.1" &&
          [r.url(), r.postData() || "", JSON.stringify(r.headers())].some(
            (v) =>
              v.includes(key) ||
              v.includes(query) ||
              v.includes(encodeURIComponent(query)),
          )
        )
          a.private_input_to_atlas = true;
        if (
          u.hostname === "api.siliconflow.cn" &&
          u.pathname.endsWith("/chat/completions")
        ) {
          const body = r.postDataJSON();
          a.requests.push({
            model: body.model,
            format: body.response_format?.type,
            enable_thinking: body.enable_thinking,
            thinking_budget: body.thinking_budget,
            max_tokens: body.max_tokens,
            submitted_at: new Date().toISOString(),
          });
        }
      });
      page.on("response", (r) => {
        if (!r.url().endsWith("/chat/completions")) return;
        const request = r.request().postDataJSON();
        const i = a.requests.length;
        captures.push(
          (async () => {
            try {
              const { content, usage } = responseContent(await r.text());
              if (content.includes(key)) throw new Error("Secret in response");
              await writeFile(
                `${dir}/case-${caseId}-response-${i}.json`,
                JSON.stringify(
                  { request, content, usage, status: r.status() },
                  null,
                  2,
                ),
              );
            } catch {}
          })(),
        );
      });
      try {
        await page.goto(baseURL);
        a.bundle = await page
          .locator("script[type=module]")
          .getAttribute("src");
        const earlierBundles = report.attempts
          .filter((previous) => previous !== a && previous.bundle)
          .map((previous) => previous.bundle);
        if (earlierBundles.some((bundle) => bundle !== a.bundle))
          throw new Error(
            "The frontend changed during this matrix. Start a new run; completed cases are preserved.",
          );
        await page
          .getByRole("button", { name: "Settings", exact: true })
          .click();
        await page.getByLabel("SiliconFlow API key", { exact: true }).fill(key);
        if (!report.available_models.length) {
          await page
            .getByRole("button", {
              name: "Load my available models",
              exact: true,
            })
            .click();
          await page
            .getByText(/models available to your account/)
            .waitFor({ timeout: 30000 });
          report.available_models = await page
            .locator("#exploration-models option")
            .evaluateAll((ns) => ns.map((n) => n.value));
          console.log(
            JSON.stringify({
              requested_models: models,
              available: models.filter((id) =>
                report.available_models.includes(id),
              ),
            }),
          );
        }
        if (!report.available_models.includes(model)) {
          a.errors.push("Exact requested model unavailable; no substitution.");
          await flush();
          continue;
        }
        await page.getByLabel("Model ID", { exact: true }).fill(model);
        await page
          .getByLabel("Remember API key on this device", { exact: false })
          .uncheck();
        await page
          .getByRole("button", { name: "Save settings", exact: true })
          .click();
        await page
          .getByRole("button", { name: "Trace a discovery", exact: true })
          .click();
        await page
          .getByLabel("Which discovery would you like to trace?", {
            exact: true,
          })
          .fill(query);
        const submit = page.getByRole("button", {
          name: "Build research map",
          exact: true,
        });
        await expect(submit).toBeEnabled({ timeout: 10000 });
        const start = Date.now();
        await submit.click();
        let lastStage = "",
          lastLog = 0;
        console.log(
          JSON.stringify({ case: caseId, query, model, event: "started" }),
        );
        while (
          Date.now() - start <
          protocol.browser_attempt_ceiling_seconds * 1000
        ) {
          const heading = await page
              .locator(".research-progress h2")
              .textContent()
              .catch(() => ""),
            detail = await page
              .locator(".explore-progress")
              .textContent()
              .catch(() => ""),
            elapsed = (Date.now() - start) / 1000;
          if (heading !== lastStage) {
            a.progress.push({ seconds: elapsed, heading, detail });
            lastStage = heading;
          }
          if (elapsed - lastLog > 20) {
            console.log(
              JSON.stringify({
                case: caseId,
                seconds: Math.round(elapsed),
                heading,
                detail,
              }),
            );
            lastLog = elapsed;
          }
          if (
            a.first_insight_seconds === null &&
            (await page.locator(".personal-result").isVisible())
          )
            a.first_insight_seconds = elapsed;
          const count = await page
            .locator(".research-counts div")
            .filter({ has: page.getByText("Connections", { exact: true }) })
            .locator("dd")
            .textContent()
            .catch(() => null);
          if (a.first_connection_seconds === null && Number(count) > 0)
            a.first_connection_seconds = elapsed;
          if (heading === "Evidence check finished.") {
            a.finished = true;
            break;
          }
          if (
            heading === "Your map is available." ||
            heading === "Continue from where you stopped."
          ) {
            a.errors.push(
              heading,
              ...(await page.getByRole("alert").allTextContents()),
            );
            break;
          }
          if (await page.getByRole("alert").isVisible()) {
            a.errors.push(...(await page.getByRole("alert").allTextContents()));
            break;
          }
          await new Promise((r) => setTimeout(r, 1000));
        }
        a.seconds = (Date.now() - start) / 1000;
        if (!a.finished) {
          const pause = page
            .getByRole("region", { name: "Exploration progress", exact: true })
            .getByRole("button", { name: "Pause exploration", exact: true });
          if (await pause.isVisible()) {
            a.errors.push(
              "Browser acceptance ceiling reached; explicitly paused.",
            );
            await pause.click();
          }
        }
        if (
          await page
            .getByRole("button", { name: "Download map", exact: true })
            .isVisible()
        ) {
          const download = page.waitForEvent("download");
          await page
            .getByRole("button", { name: "Download map", exact: true })
            .click();
          const map = JSON.parse(
            await readFile(await (await download).path(), "utf8"),
          );
          if (JSON.stringify(map).includes(key))
            throw new Error("Credential found in exported map");
          await writeFile(
            `${dir}/case-${caseId}-map.json`,
            JSON.stringify(map, null, 2),
          );
          a.receipts = map.receipts;
          a.nodes = map.nodes.length;
          a.connections = map.relations.length;
          a.check_status = map.check_status;
          a.completion = map.completion;
          a.lineage = lineage(map.nodes, map.relations);
          a.title = map.title;
          a.structural_target_met = Boolean(
            a.finished &&
            map.check_status === "completed" &&
            a.lineage.hasBackbone &&
            a.lineage.connected >= map.nodes.length * 0.8,
          );
          a.timing_target_met = Boolean(
            a.first_insight_seconds !== null &&
            a.first_insight_seconds <= 60 &&
            a.seconds <= 180,
          );
          await page.getByRole("button", { name: "Map", exact: true }).click();
          await page.locator(".personal-result").scrollIntoViewIfNeeded();
          await page.screenshot({ path: `${dir}/case-${caseId}-map.png` });
          if (map.relations.length) {
            await page.locator(".personal-connections summary").click();
            await page.locator(".personal-connections button").first().click();
            await page
              .getByRole("heading", {
                name: "Why is this connection here?",
                exact: true,
              })
              .waitFor();
            await page
              .locator(".personal-evidence blockquote")
              .first()
              .waitFor();
            a.arrow_inspector = true;
            await page
              .getByRole("button", {
                name: "Close personal map inspector",
                exact: true,
              })
              .click();
          }
          await page.getByRole("button", { name: "List", exact: true }).click();
          if (map.nodes.length) {
            await page.locator(".personal-node-list button").first().click();
            await page
              .locator(".personal-evidence blockquote")
              .first()
              .waitFor();
            a.insight_inspector = true;
          }
        } else
          a.receipt_text = await page
            .locator(".exploration-receipts")
            .textContent()
            .catch(() => null);
      } catch (e) {
        a.errors.push(String(e.message || e).replaceAll(key, "[redacted]"));
      } finally {
        const observations = await page
          .evaluate(() => window.__qaResponses || [])
          .catch(() => []);
        if (JSON.stringify(observations).includes(key))
          throw new Error("Credential found in QA observations");
        await writeFile(
          `${dir}/case-${caseId}-observations.json`,
          JSON.stringify(observations, null, 2),
        );
        await context.close();
        await Promise.allSettled(captures);
        a.finished_at = new Date().toISOString();
        await flush();
        console.log(
          JSON.stringify({
            case: caseId,
            query,
            model,
            seconds: a.seconds,
            nodes: a.nodes,
            connections: a.connections,
            foundation_route: a.lineage?.hasBackbone,
            structural_target_met: a.structural_target_met,
            timing_target_met: a.timing_target_met,
            errors: a.errors,
          }),
        );
      }
    }
} finally {
  report.finished_at = new Date().toISOString();
  await flush();
  await browser.close();
}
