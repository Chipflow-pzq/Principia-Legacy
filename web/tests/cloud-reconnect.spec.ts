import { test, expect } from "@playwright/test";

test("a cold page automatically recovers and preserves its query", async ({
  page,
}) => {
  let available = false;
  let attempts = 0;
  await page.route("**/api/**", async (route) => {
    if (available) return route.continue();
    attempts++;
    await route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({
        code: "cloud_reconnecting",
        error: "Reconnecting",
      }),
    });
  });
  await page.goto("/#release=1.5.0-review4&q=neuronal%20state%20space");
  await expect(
    page
      .getByRole("status")
      .filter({ hasText: "Reconnecting to your cloud atlas" }),
  ).toBeVisible();
  await expect(
    page.getByRole("textbox", { name: "Search the atlas" }),
  ).toHaveValue("neuronal state space");
  available = true;
  await expect(
    page.getByRole("heading", {
      name: "Dimensionality reduction for large-scale neural recordings",
    }),
  ).toBeVisible({ timeout: 15000 });
  await expect(page.locator(".connection-notice")).toHaveCount(0);
  expect(attempts).toBeGreaterThan(0);
  await expect(page.locator(".error")).toHaveCount(0);
});

test("a dropped connection retries the current search and cancels an old one", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.locator(".flagship-card")).toHaveCount(5);
  let available = false;
  const attempts: string[] = [];
  await page.route("**/api/search?**", async (route) => {
    attempts.push(route.request().url());
    if (available) return route.continue();
    await route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ code: "cloud_reconnecting" }),
    });
  });
  const input = page.getByRole("textbox", { name: "Search the atlas" });
  await input.fill("Hamiltonian mechanics");
  await expect(page.locator(".connection-notice")).toBeVisible();
  await input.fill("neuronal state space");
  available = true;
  await expect(
    page.getByRole("heading", {
      name: "Dimensionality reduction for large-scale neural recordings",
    }),
  ).toBeVisible({ timeout: 15000 });
  await expect(page.locator(".connection-notice")).toHaveCount(0);
  await expect(input).toHaveValue("neuronal state space");
  expect(attempts.filter((url) => url.includes("Hamiltonian")).length).toBe(1);
});
