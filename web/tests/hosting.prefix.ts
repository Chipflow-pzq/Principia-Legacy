import { test, expect } from "@playwright/test";

test("hosted build keeps assets, search, profiles and reload within its mount", async ({
  page,
}, testInfo) => {
  const requests: string[] = [];
  const failures: string[] = [];
  page.on("pageerror", (error) => failures.push(error.message));
  page.on("response", (response) => {
    if (response.status() >= 400)
      failures.push(`${response.status()} ${response.url()}`);
  });
  await page.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    requests.push(url.pathname);
    expect(url.origin).toBe("http://127.0.0.1:18766");
    expect(url.pathname).toMatch(/^\/web\/legacy\//);
    await route.continue();
  });
  await page.goto("./");
  await expect(page.locator(".flagship-card")).toHaveCount(5);
  await expect(page.locator(".local-status")).toHaveText("Public · read-only");
  // The compact mobile header intentionally hides this nonessential badge.
  if (testInfo.project.name === "desktop")
    await expect(page.locator(".local-status")).toBeVisible();
  await page
    .getByRole("textbox", { name: "Search the atlas" })
    .fill("Einstein");
  await page
    .locator(".person-card")
    .filter({ hasText: "Albert Einstein" })
    .click();
  await expect(
    page.getByRole("heading", { name: "Albert Einstein", exact: true }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Albert Einstein", exact: true }),
  ).toBeVisible();
  await page.locator(".person-page .work-card").first().click();
  await expect(page.locator(".work-page h1")).toBeVisible();
  await page.reload();
  await expect(page.locator(".work-page h1")).toBeVisible();
  await page
    .getByRole("button", { name: "← Back to scientist profile" })
    .click();
  await expect(page.locator(".person-page h1")).toHaveText("Albert Einstein");
  await page.locator(".person-page .node-list button").first().click();
  const inspector = page.getByRole("complementary", {
    name: "Record inspector",
  });
  await expect(inspector).toBeVisible();
  await inspector.locator(".topic-link").first().click();
  await expect(page.getByRole("img")).toHaveAttribute(
    "aria-label",
    /[1-9][0-9]* contributions/,
  );
  await page
    .getByRole("button", { name: "Trace a discovery", exact: true })
    .click();
  await expect(
    page.getByLabel("Which discovery would you like to trace?"),
  ).toBeVisible();
  await page.getByRole("button", { name: "Settings", exact: true }).click();
  await expect(
    page.getByLabel("SiliconFlow API key", { exact: true }),
  ).toHaveValue("");
  const index = await page.request.get(
    "./api/exploration-index?limit=2&release=1.2.0-exploratory",
  );
  expect(index.ok()).toBe(true);
  expect((await index.json()).entries).toHaveLength(2);
  expect(requests.some((path) => path.includes("/api/search"))).toBe(true);
  expect(requests.some((path) => path.includes("/assets/"))).toBe(true);
  expect(failures).toEqual([]);
});
