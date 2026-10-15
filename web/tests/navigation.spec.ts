import { test, expect } from "@playwright/test";
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
test("scientist directory remembers its query when reading a profile and reloading", async ({
  page,
}) => {
  await page.getByRole("button", { name: "Scientists", exact: true }).click();
  await page
    .getByRole("textbox", { name: "Find a scientist or contributor" })
    .fill("Einstein");
  await page
    .locator(".person-card")
    .filter({ hasText: "Albert Einstein" })
    .click();
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Albert Einstein", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", {
      name: "← All scientists & contributors",
      exact: true,
    })
    .click();
  await expect(
    page.getByRole("textbox", { name: "Find a scientist or contributor" }),
  ).toHaveValue("Einstein");
  await expect(
    page.locator(".person-card").filter({ hasText: "Albert Einstein" }),
  ).toBeVisible();
});
test("search survives reading, next result, closing, browser back and reload", async ({
  page,
}) => {
  await page
    .getByRole("textbox", { name: "Search contributions" })
    .fill("general relativity");
  const result = page
    .locator(".result-card")
    .filter({ hasText: "Consistency tests of general relativity" });
  await result.click();
  const inspector = page.getByRole("complementary", {
    name: "Record inspector",
  });
  await expect(
    inspector.getByRole("heading", {
      name: "Consistency tests of general relativity in the strong-field regime",
      exact: true,
    }),
  ).toBeVisible();
  await expect(inspector.locator(".topic-link")).toHaveCount(2);
  await page
    .getByRole("button", { name: "Next search result", exact: true })
    .click();
  await expect(
    inspector.getByRole("heading", {
      name: "Consistency tests of general relativity in the strong-field regime",
      exact: true,
    }),
  ).toHaveCount(0);
  await page
    .getByRole("button", { name: "← Back to results", exact: true })
    .click();
  await expect(inspector).toHaveCount(0);
  await expect(page.locator(".result-card").first()).toBeVisible();
  await result.click();
  await inspector
    .locator(".topic-link")
    .filter({ hasText: "General relativity" })
    .last()
    .click();
  await expect(
    page.getByRole("heading", { name: "General relativity", exact: true }),
  ).toBeVisible();
  await page.goBack();
  await expect(
    page.getByRole("textbox", { name: "Search contributions" }),
  ).toHaveValue("general relativity");
  await expect(inspector).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("textbox", { name: "Search contributions" }),
  ).toHaveValue("general relativity");
  await expect(inspector).toBeVisible();
});
test("scientist search opens a sourced profile, linked ideas and topics", async ({
  page,
}) => {
  await page
    .getByRole("textbox", { name: "Search contributions" })
    .fill("Einstein");
  await page
    .locator(".person-card")
    .filter({ hasText: "Albert Einstein" })
    .click();
  await expect(
    page.getByRole("heading", { name: "Albert Einstein", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".person-bio")).toContainText("1923");
  await expect(page.locator(".person-page .topic-link").first()).toBeVisible();
  await page.locator(".person-page .node-list button").first().click();
  await expect(
    page.getByRole("complementary", { name: "Record inspector" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Close inspector", exact: true })
    .click();
  await page
    .getByRole("button", { name: "← Back to search results", exact: true })
    .click();
  await expect(page.locator(".search-results .person-card")).toBeVisible();
});
test("Hamiltonian mechanics is discoverable as a topic and via Hamilton", async ({
  page,
}) => {
  await page
    .getByRole("textbox", { name: "Search contributions" })
    .fill("Hamiltonian mechanics");
  await expect(
    page
      .locator(".search-results .topic-link")
      .filter({ hasText: "Hamiltonian mechanics" }),
  ).toBeVisible();
  await page
    .getByRole("textbox", { name: "Search contributions" })
    .fill("Hamilton");
  await page
    .locator(".person-card")
    .filter({ hasText: "William Rowan Hamilton" })
    .click();
  await expect(
    page.getByRole("heading", { name: "William Rowan Hamilton", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".person-page .node-list button")).not.toHaveCount(
    0,
  );
});
test("search paginates broad results without discarding the query", async ({
  page,
}) => {
  await page
    .getByRole("textbox", { name: "Search contributions" })
    .fill("model");
  await expect(page.locator(".result-card")).toHaveCount(40);
  const first = await page.locator(".result-card h3").first().innerText();
  await page.getByRole("button", { name: "Next results", exact: true }).click();
  await expect(page.locator(".result-card h3").first()).not.toHaveText(first);
  await expect(
    page.getByRole("textbox", { name: "Search contributions" }),
  ).toHaveValue("model");
  await page
    .getByRole("button", { name: "Previous results", exact: true })
    .click();
  await expect(page.locator(".result-card h3").first()).toHaveText(first);
});

test("search and tracing work while the initial catalogue is still loading", async ({
  page,
}) => {
  let finishLoading!: () => void;
  const loading = new Promise<void>((resolve) => {
    finishLoading = resolve;
  });
  await page.route("**/api/info*", async (route) => {
    await loading;
    await route.continue();
  });
  try {
    await page.goto("/");
    await page
      .getByRole("textbox", { name: "Search contributions" })
      .fill("attention");
    await page.locator(".result-card").first().click();
    await page.getByRole("button", { name: "Trace its connections ↗" }).click();
    await expect(
      page.getByRole("button", { name: "Back to this topic" }),
    ).toBeVisible();
    expect(
      new URLSearchParams(new URL(page.url()).hash.slice(1)).get("release"),
    ).not.toBe("working");
  } finally {
    finishLoading();
  }
});
