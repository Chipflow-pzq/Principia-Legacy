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
test("topic return restores catalogue filters, page, scroll and focus after reload", async ({
  page,
}) => {
  await page.getByLabel("Coverage", { exact: true }).selectOption("available");
  await page.getByRole("button", { name: "Next topics", exact: true }).click();
  await expect(page).toHaveURL(/catalogoffset=60/);
  const card = page.locator(".dossier-tile").first();
  await expect(card).toBeVisible();
  const id = await card.getAttribute("id");
  await card.click();
  await expect(page.locator(".dossier-view h1")).toBeVisible();
  await page.getByRole("button", { name: "List", exact: true }).click();
  await page.locator(".node-list button").first().click();
  await expect(
    page.getByRole("complementary", { name: "Record inspector" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Close inspector", exact: true })
    .click();
  await page.reload();
  await page
    .getByRole("button", { name: "← Back to topics", exact: true })
    .click();
  await expect(page.getByLabel("Coverage", { exact: true })).toHaveValue(
    "available",
  );
  await expect(page).toHaveURL(/catalogoffset=60/);
  await expect(page.locator(`#${id}`)).toBeFocused();
  expect(await page.evaluate(() => window.scrollY)).toBeGreaterThan(100);
  await page.reload();
  await expect(page.getByLabel("Coverage", { exact: true })).toHaveValue(
    "available",
  );
  await expect(page).toHaveURL(/catalogoffset=60/);
});
test("human-review filter survives reload and shows an honest empty state", async ({
  page,
}) => {
  const toggle = page.getByRole("checkbox", { name: "Human-reviewed only" });
  await toggle.check();
  await expect(page).toHaveURL(/human=1/);
  await page.reload();
  await expect(toggle).toBeChecked();
  await page
    .getByRole("textbox", { name: "Search the atlas" })
    .fill("attention");
  await expect(page.locator(".result-card")).toHaveCount(0);
  await toggle.uncheck();
  await expect(page).toHaveURL(/human=0/);
  await expect(page.locator(".result-card").first()).toBeVisible();
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

test("a work's contributor returns to that work after reload", async ({
  page,
}) => {
  await page
    .getByRole("textbox", { name: "Search the atlas" })
    .fill("Alan Turing");
  await page.getByRole("button", { name: /^Works ·/ }).click();
  await page
    .locator(".work-card")
    .filter({ hasText: /On computable numbers/i })
    .click();
  await expect(page.locator(".work-page h1")).toContainText(
    /On computable numbers/i,
  );
  const workURL = page.url();
  await page
    .locator(".work-page")
    .getByRole("button", { name: /Alan.*Turing.*↗/ })
    .click();
  await expect(page.locator(".person-page h1")).toContainText("Alan");
  await page.reload();
  await page
    .getByRole("button", { name: "← Back to previous view", exact: true })
    .click();
  await expect(page).toHaveURL(workURL);
  await expect(page.locator(".work-page h1")).toContainText(
    /On computable numbers/i,
  );
  await page.getByRole("button", { name: "← Back to search results" }).click();
  await expect(
    page.getByRole("textbox", { name: "Search the atlas" }),
  ).toHaveValue("Alan Turing");
  await expect(page.getByRole("button", { name: /^Works ·/ })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
});
test("search survives reading, next result, closing, browser back and reload", async ({
  page,
}) => {
  await page
    .getByRole("textbox", { name: "Search the atlas" })
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
    .getByRole("button", { name: "Back to search results", exact: true })
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
    page.getByRole("textbox", { name: "Search the atlas" }),
  ).toHaveValue("general relativity");
  await expect(inspector).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("textbox", { name: "Search the atlas" }),
  ).toHaveValue("general relativity");
  await expect(inspector).toBeVisible();
});

test("a topic link works when its search result arrives before the catalogue", async ({
  page,
}) => {
  let releaseCatalogue!: () => void;
  const held = new Promise<void>((resolve) => {
    releaseCatalogue = resolve;
  });
  let calls = 0;
  await page.route("**/api/dossiers*", async (route) => {
    if (++calls === 1) await held;
    await route.continue();
  });
  try {
    await page.goto("/");
    await page
      .getByRole("textbox", { name: "Search the atlas" })
      .fill("general relativity");
    await page
      .locator(".result-card")
      .filter({ hasText: "Consistency tests of general relativity" })
      .click();
    const inspector = page.getByRole("complementary", {
      name: "Record inspector",
    });
    await inspector
      .locator(".topic-link")
      .filter({ hasText: "General relativity" })
      .last()
      .click();
    await expect(
      page.getByRole("heading", { name: "General relativity", exact: true }),
    ).toBeVisible();
    // Navigation may resolve from the compact overview or individual topic API.
    // It must finish while the unrelated catalogue request is still held.
    await expect(
      page.getByRole("textbox", { name: "Search the atlas" }),
    ).toHaveValue("");
  } finally {
    releaseCatalogue();
  }
});
test("scientist search opens a sourced profile, linked ideas and topics", async ({
  page,
}) => {
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
  await expect(
    page
      .locator(".search-results .person-card")
      .filter({ hasText: "Albert Einstein" }),
  ).toBeVisible();
});
test("Hamiltonian mechanics is discoverable as a topic and via Hamilton", async ({
  page,
}) => {
  await page
    .getByRole("textbox", { name: "Search the atlas" })
    .fill("Hamiltonian mechanics");
  await expect(
    page
      .locator(".search-results .topic-link")
      .filter({ hasText: "Hamiltonian mechanics" }),
  ).toBeVisible();
  await page
    .getByRole("textbox", { name: "Search the atlas" })
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
  await page.getByRole("textbox", { name: "Search the atlas" }).fill("model");
  await page.getByRole("button", { name: /^Ideas ·/ }).click();
  await expect(page.locator(".result-card")).toHaveCount(40);
  const first = await page.locator(".result-card h3").first().innerText();
  await page.getByRole("button", { name: "Next results", exact: true }).click();
  await expect(page.locator(".result-card h3").first()).not.toHaveText(first);
  await expect(
    page.getByRole("textbox", { name: "Search the atlas" }),
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
    const searched = page.waitForResponse(
      (r) =>
        r.ok() &&
        r.url().includes("/api/search") &&
        r.url().includes("attention"),
    );
    await page
      .getByRole("textbox", { name: "Search the atlas" })
      .fill("attention");
    const snapshot = (await (await searched).json()).release_id;
    await page.locator(".result-card").first().click();
    await page.getByRole("button", { name: "Trace its connections ↗" }).click();
    await expect(
      page.getByRole("button", { name: "Back to this topic" }),
    ).toBeVisible();
    expect(
      new URLSearchParams(new URL(page.url()).hash.slice(1)).get("release"),
    ).toBe(snapshot);
  } finally {
    finishLoading();
  }
});
