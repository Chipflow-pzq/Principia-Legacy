import { test, expect } from "@playwright/test";

test("neuroscience wording finds a transparent topic and real works", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("textbox", { name: "Search the atlas" })
    .fill("neuronal state space");
  await expect(
    page.getByRole("button", {
      name: /Neural population dynamics and state-space analysis/,
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", {
      name: "Dimensionality reduction for large-scale neural recordings",
    }),
  ).toBeVisible();
  await expect(page.getByText("No matches in this release")).toHaveCount(0);
  await page
    .getByRole("button", {
      name: /Neural population dynamics and state-space analysis/,
    })
    .click();
  await expect(page.locator(".dossier-view h1")).toContainText(
    "Neural population dynamics",
  );
  await expect(page.locator(".map-toolbar")).toBeVisible();
  await expect(page.locator(".dossier-stats")).not.toContainText(
    "0 contributions",
  );
});

test("area choices are optional, bounded and searchable", async ({ page }) => {
  await page.goto("/");
  await expect(
    page.getByRole("combobox", { name: "Area", exact: true }),
  ).toHaveCount(0);
  await expect(page.locator(".area-picker")).not.toHaveAttribute("open", "");
  await page.getByText("Refine by area", { exact: true }).click();
  await expect(
    page.getByRole("searchbox", { name: "Find an area" }),
  ).toBeEnabled({ timeout: 15000 });
  await expect(page.locator(".area-choices button")).toHaveCount(8);
  await page
    .getByRole("searchbox", { name: "Find an area" })
    .fill("neuroscience");
  await page.getByRole("button", { name: "Neuroscience", exact: true }).click();
  await expect(page.locator(".dossier-tile")).toHaveCount(2);
  await expect(
    page
      .locator(".dossier-tile")
      .filter({ hasText: "Neural population dynamics" }),
  ).toContainText("Neural population dynamics");
  await page.reload();
  await expect(page.locator(".area-picker summary")).toContainText(
    "Neuroscience",
  );
  await page.locator(".area-picker summary").click();
  await page.getByRole("button", { name: "All areas", exact: true }).click();
  await expect(page.locator(".dossier-tile")).toHaveCount(60);
});

test("cloud semantic search handles a paraphrase without an LLM key", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.locator(".local-status")).toContainText("Private cloud");
  await page
    .getByRole("textbox", { name: "Search the atlas" })
    .fill("brain activity as trajectories in a low dimensional space");
  await expect(page.getByText(/Related by meaning/)).toBeVisible({
    timeout: 15000,
  });
  await expect(page.getByText("No matches in this release")).toHaveCount(0);
  await expect(
    page.getByRole("heading", {
      name: "Dimensionality reduction for large-scale neural recordings",
    }),
  ).toBeVisible();
});

test("a pinned reading view does not wait for homepage suggestions", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("textbox", { name: "Search the atlas" })
    .fill("general relativity");
  await page
    .locator(".result-card")
    .filter({ hasText: "Consistency tests of general relativity" })
    .click();
  await expect(page.locator(".inspector .topic-link")).toHaveCount(2);
  let releaseOverview!: () => void;
  const held = new Promise<void>((resolve) => {
    releaseOverview = resolve;
  });
  await page.route("**/api/topic-overview*", async (route) => {
    await held;
    await route.continue();
  });
  try {
    await page.reload();
    await expect(page.locator(".inspector .topic-link")).toHaveCount(2);
    await expect(page.locator(".inspector h2").first()).toContainText(
      "Consistency tests",
    );
  } finally {
    releaseOverview();
  }
});
