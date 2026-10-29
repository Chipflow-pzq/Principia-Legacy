import { test, expect } from "@playwright/test";

// Read-only production checks. No keys, provider calls, writes or saved maps.
test("published neuroscience route has insights, arrows and a continuous return", async ({ page }, info) => {
  const failures: string[] = [];
  page.on("pageerror", error => failures.push(error.message));
  await page.goto("./");
  await page.getByRole("textbox", { name: "Search the atlas" }).fill("neuronal group communication");
  const topic = page.getByRole("button", { name: /Communication between neural populations/ });
  await expect(topic).toContainText(/\d+ insights/);
  await topic.click();
  await expect(page.locator(".dossier-view h1")).toHaveText("Communication between neural populations");
  await expect(page.locator(".map-toolbar")).toBeVisible();
  await page.getByRole("button", { name: "Start with the main result" }).click();
  await expect(page.locator(".inspector")).toContainText(/V1|V2/);
  await page.locator(".inspector").getByRole("button", { name: "Back to search results" }).click();
  await expect(page.getByRole("textbox", { name: "Search the atlas" })).toHaveValue("neuronal group communication");
  await expect(page.getByRole("heading", { name: "Cortical areas interact through a communication subspace" })).toBeVisible();
  const graph = await page.request.get("./api/neighborhood?dossier=B3002");
  const data = await graph.json();
  expect(data.release_id).toBe("1.5.0-exploratory");
  expect(data.contributions.length).toBe(11);
  expect(data.relations.length).toBe(8);
  const arrow = await page.request.get("./api/relations/" + data.relations[0].id);
  expect(arrow.ok()).toBe(true);
  await page.screenshot({ path: `test-results/public-neuroscience-${info.project.name}.png` });
  expect(failures).toEqual([]);
});

test("public semantic search, formulas and historical links survive publication", async ({ page }, info) => {
  await page.goto("./#q=how+populations+of+brain+cells+talk");
  await expect(page.locator(".result-card").first()).toBeVisible();
  const result = await page.request.get("./api/search?q=how+populations+of+brain+cells+talk");
  const search = await result.json();
  expect(search.search_interpretation.match_mode).toBe("semantic");
  expect(search.works.map((work: {id: string}) => work.id)).toContain("w-semedo-communication-subspace");
  await page.goto("./#node=n-c39b57d578d34320");
  await expect(page.locator(".inspector h2")).toContainText("Price versus average cost");
  await expect(page.locator(".inspector")).toContainText("At a price of $5");
  await expect(page.locator(".inspector .katex").first()).toBeVisible();
  await expect(page.locator(".katex-error")).toHaveCount(0);
  await page.goto("./#release=1.4.1-exploratory&q=neuronal+state+space");
  await expect(page.getByRole("button", { name: "Open the latest atlas" })).toBeVisible();
  await page.getByRole("button", { name: "Open the latest atlas" }).click();
  await expect(page).toHaveURL(/release=1.5.0-exploratory/);
  await expect(page.getByRole("textbox", { name: "Search the atlas" })).toHaveValue("neuronal state space");
  await expect(page.locator(".result-card").first()).toBeVisible();
  await page.screenshot({ path: `test-results/public-semantic-${info.project.name}.png` });
});
