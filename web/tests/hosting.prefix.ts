import { test, expect } from "@playwright/test";

test("hosted build keeps assets, search, profiles and reload within its mount", async ({ page }, testInfo) => {
  const requests: string[] = [];
  const failures: string[] = [];
  page.on("pageerror", error => failures.push(error.message));
  page.on("response", response => {
    if (response.status() >= 400) failures.push(`${response.status()} ${response.url()}`);
  });
  await page.route("**/*", async route => {
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
  await page.getByRole("textbox", { name: "Search contributions" }).fill("Einstein");
  await page.locator(".person-card").filter({ hasText: "Albert Einstein" }).click();
  await expect(page.getByRole("heading", { name: "Albert Einstein", exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByRole("heading", { name: "Albert Einstein", exact: true })).toBeVisible();
  await page.locator(".person-page .node-list button").first().click();
  const inspector = page.getByRole("complementary", { name: "Record inspector" });
  await expect(inspector).toBeVisible();
  await inspector.locator(".topic-link").first().click();
  await expect(page.getByRole("img")).toHaveAttribute("aria-label", /[1-9][0-9]* contributions/);
  expect(requests.some(path => path.includes("/api/search"))).toBe(true);
  expect(requests.some(path => path.includes("/assets/"))).toBe(true);
  expect(failures).toEqual([]);
});
