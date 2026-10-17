import { test, expect } from "@playwright/test";
import { resolve } from "node:path";

test.beforeEach(async ({ page }) => {
  await page.route("**/*", async (route) => {
    expect(new URL(route.request().url()).hostname).toBe("127.0.0.1");
    await route.continue();
  });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Ideas do not stand alone." }),
  ).toBeVisible();
});

test("discovery choices follow the selected subject and restore on reload", async ({
  page,
}) => {
  await page.getByRole("button", { name: /^Physics(?: |$)/ }).click();
  await expect(page.locator(".flagship-card")).toHaveCount(5);
  for (const card of await page.locator(".flagship-card").all()) {
    await expect(card.locator(".eyebrow")).toHaveText(/Physics/i);
  }
  await page.reload();
  await expect(page.locator(".pillar-button.selected")).toHaveText(/Physics/);
  await expect(page.locator(".flagship-card .eyebrow").first()).toHaveText(
    /Physics/i,
  );
  await page.getByRole("button", { name: /All subjects/ }).click();
  expect(
    new Set(await page.locator(".flagship-card .eyebrow").allTextContents())
      .size,
  ).toBe(5);
});

test("typo search reaches a real person and work, preserving the results", async ({
  page,
}, testInfo) => {
  await page
    .getByRole("textbox", { name: "Search the atlas" })
    .fill("Allan Turing");
  await expect(page.locator(".search-interpretation")).toContainText(
    "alan turing",
  );
  await expect(page.locator(".search-filters button")).toHaveCount(5);
  if (testInfo.project.name === "desktop")
    await page.screenshot({
      path: resolve("../docs/screenshots/reader-search.png"),
    });
  await page.getByRole("button", { name: /^Works ·/ }).click();
  const paper = page
    .locator(".work-card")
    .filter({ hasText: /On computable numbers/i });
  await paper.click();
  await expect(page.locator(".work-page h1")).toContainText(
    /On computable numbers/i,
  );
  await expect(
    page.locator(".work-page .node-list button").first(),
  ).toBeVisible();
  if (testInfo.project.name === "desktop")
    await page.screenshot({
      path: resolve("../docs/screenshots/reader-work.png"),
    });
  await page.reload();
  await expect(page.locator(".work-page h1")).toContainText(
    /On computable numbers/i,
  );
  await page.getByRole("button", { name: "← Back to browsing" }).click();
  await expect(page.getByRole("button", { name: /^Works ·/ })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await expect(
    page.getByRole("textbox", { name: "Search the atlas" }),
  ).toHaveValue("Allan Turing");
  await page
    .getByRole("button", { name: /^Scientists & contributors ·/ })
    .click();
  await page.locator(".person-card").filter({ hasText: "Alan Turing" }).click();
  await expect(page.locator(".person-page h1")).toHaveText("Alan Turing");
  await expect(
    page
      .locator(".person-page .work-card")
      .filter({ hasText: /On computable numbers/i }),
  ).toBeVisible();
});

test("a work exposes sourced ideas and links back to its topic", async ({
  page,
}) => {
  await page
    .getByRole("textbox", { name: "Search the atlas" })
    .fill("von neuman");
  await page.getByRole("button", { name: /^Works ·/ }).click();
  await page
    .locator(".work-card")
    .filter({ hasText: "First Draft of a Report on the EDVAC" })
    .click();
  await page.locator(".work-page .node-list button").first().click();
  const inspector = page.getByRole("complementary", {
    name: "Record inspector",
  });
  await expect(inspector.locator(".work-card").first()).toBeVisible();
  await page
    .getByRole("button", { name: "Close inspector", exact: true })
    .click();
  await page.locator(".work-page .topic-link").first().click();
  await expect(page.locator(".dossier-view h1")).toContainText(
    "Stored programs and computer architecture",
  );
  await expect(page.locator(".graph")).toBeVisible();
});

test("concept search and catalog-only topics disclose extraction gaps", async ({
  page,
}) => {
  await page
    .getByRole("textbox", { name: "Search the atlas" })
    .fill("what is genetic scissors");
  await expect(page.locator(".search-interpretation").last()).toContainText(
    /crispr|gene editing/i,
  );
  await expect(page.locator(".result-card").first()).toBeVisible();
  await page
    .getByRole("textbox", { name: "Search the atlas" })
    .fill("Interactive Linear Algebra");
  await page
    .locator(".work-card")
    .filter({ hasText: "Interactive Linear Algebra" })
    .click();
  await expect(page.locator(".work-page")).toContainText(
    "insight extraction is still pending",
  );
  await page.locator(".work-page .topic-link").first().click();
  await expect(page.locator(".dossier-view")).toContainText(
    "insight extraction",
  );
  await expect(page.locator(".graph")).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "← All topics" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "← All topics" }).click();
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Browse all topics" }),
  ).toBeVisible();
});

test("catalog pages fit narrow screens without horizontal overflow", async ({
  page,
}) => {
  await page
    .getByRole("textbox", { name: "Search the atlas" })
    .fill("Alan Turing");
  await page
    .locator(".work-card")
    .filter({ hasText: /On computable numbers/i })
    .click();
  await expect(page.locator(".work-page h1")).toBeVisible();
  const dimensions = await page.evaluate(() => ({
    width: innerWidth,
    scroll: document.documentElement.scrollWidth,
  }));
  expect(dimensions.scroll).toBeLessThanOrEqual(dimensions.width + 1);
});
