import { test, expect } from "@playwright/test";
import { resolve } from "node:path";

test("currency and equations stay readable in an economics explanation", async ({
  page,
}, info) => {
  await page.goto("/#node=n-c39b57d578d34320&release=1.5.0-review5");
  await expect(page.locator(".inspector h2")).toContainText(
    "Price versus average cost",
  );
  await expect(page.locator(".inspector")).toContainText("At a price of $5");
  await expect(page.locator(".inspector")).toContainText("At $2.80");
  await expect(page.locator(".inspector .katex").first()).toBeVisible();
  await expect(page.locator(".katex-error")).toHaveCount(0);
  await page.locator(".inspector .explanation").scrollIntoViewIfNeeded();
  await page.screenshot({
    path: resolve(
      `../reports/screenshots/economics-review5-${info.project.name}.png`,
    ),
  });
});

test("population communication opens actual insights and preserves the search", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("textbox", { name: "Search the atlas" })
    .fill("neuronal group communication");
  const topic = page.getByRole("button", {
    name: /Communication between neural populations/,
  });
  await expect(topic).toContainText(/\d+ insights/);
  await topic.click();
  await expect(page.locator(".dossier-view h1")).toHaveText(
    "Communication between neural populations",
  );
  await expect(page.locator(".map-toolbar")).toBeVisible();
  await page
    .getByRole("button", { name: "Start with the main result" })
    .click();
  await expect(page.locator(".inspector")).toContainText(/V1|V2/);
  await page
    .locator(".inspector")
    .getByRole("button", { name: "Back to search results" })
    .click();
  await expect(
    page.getByRole("textbox", { name: "Search the atlas" }),
  ).toHaveValue("neuronal group communication");
  await expect(
    page.getByRole("heading", {
      name: "Cortical areas interact through a communication subspace",
    }),
  ).toBeVisible();
});

test("coverage shows explained content separately from catalogue size", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByText("What is available in this atlas?", { exact: true })
    .click();
  await expect(page.locator(".coverage-table tbody tr")).toHaveCount(5);
  await expect(page.locator(".coverage-panel")).toContainText(
    "Works with insights / listed",
  );
  await expect(page.locator(".coverage-panel")).toContainText(
    "not complete field coverage",
  );
});

test("catalogue-only matches explain their limitation before opening", async ({
  page,
}) => {
  await page.goto("/#q=Emmy+Noether");
  await expect(page.locator(".topic-link").first()).toContainText(
    "Reading list only",
  );
  await expect(page.locator(".search-results")).toContainText(
    "An evidence-backed explanation",
  );
});

test("older snapshot remains readable with a path to the current atlas", async ({
  page,
}) => {
  await page.goto("/#release=1.5.0-review4&q=neuronal+state+space");
  await expect(
    page.getByRole("button", { name: "Open the latest atlas" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Open the latest atlas" }).click();
  await expect(page).toHaveURL(/release=1.5.0-review5/);
  await expect(
    page.getByRole("textbox", { name: "Search the atlas" }),
  ).toHaveValue("neuronal state space");
  await expect(page.locator(".result-card").first()).toBeVisible();
});
