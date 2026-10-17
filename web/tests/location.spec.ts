import { test, expect } from "@playwright/test";
import { normalizeLocation } from "../src/location";

test("old preview labels normalize without losing reproducible atlas links", () => {
  expect(
    normalizeLocation(
      new URL(
        "http://localhost/web/legacy/?preview=1.3.0.dev12#page=explore&release=1.2.0-exploratory",
      ),
    ),
  ).toBe("/web/legacy/#page=explore");
  expect(
    normalizeLocation(
      new URL(
        "http://localhost/?preview=old&mode=accessible#dossier=C01&release=1.2.0-exploratory",
      ),
    ),
  ).toBe("/?mode=accessible#dossier=C01&release=1.2.0-exploratory");
});

test("bare navigation and bookmarked previews reach the same personal workspace", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("button", { name: "Trace a discovery", exact: true })
    .click();
  await expect(page).toHaveURL(/\/#page=explore$/);
  await expect(page.locator("#research-query")).toBeVisible();
  await page.goto(
    "/?preview=1.3.0.dev12#page=explore&release=1.2.0-exploratory",
  );
  await expect(page).toHaveURL(/\/#page=explore$/);
  await expect(page.locator("#research-query")).toBeVisible();
  await page.getByRole("button", { name: "Settings", exact: true }).click();
  await page.getByText(/About this installation/).click();
  await expect(page.getByRole("dialog")).toContainText(
    "is a separate, reproducible collection",
  );
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
});

test("a historical topic returns intact while new research uses the current atlas", async ({
  page,
  request,
}) => {
  const info = await (await request.get("/api/info")).json();
  await page.goto("/#dossier=C01&release=1.2.0-exploratory");
  await expect(
    page.getByText("Reading an earlier version · Open current version ↗"),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Trace a discovery", exact: true })
    .click();
  await expect(page).toHaveURL(/\/#page=explore$/);
  await page.getByRole("button", { name: "Settings", exact: true }).click();
  await page.getByText(/About this installation/).click();
  await expect(page.getByRole("dialog")).toContainText(info.current_release_id);
  await page.keyboard.press("Escape");
  await page
    .getByRole("button", { name: "Browse the atlas", exact: true })
    .click();
  await expect(page).toHaveURL(/#dossier=C01&release=1\.2\.0-exploratory$/);
  await expect(
    page.getByText("Reading an earlier version · Open current version ↗"),
  ).toBeVisible();
});

test("an open tab can follow a newly available snapshot absent from its cached list", async ({
  page,
  request,
}) => {
  const current = (await (await request.get("/api/info")).json()).release_id;
  await page.route("**/api/info?**", async (route) => {
    const response = await route.fetch();
    const data = await response.json();
    if (data.release_id === "1.3.1-exploratory")
      data.releases = ["1.3.1-exploratory"];
    await route.fulfill({ response, json: data });
  });
  await page.goto("/#dossier=C01&release=1.3.1-exploratory");
  await expect(page.locator(".dossier-view h1")).toContainText("Transformer");
  await page.goto("/#dossier=C01&release=" + current);
  await expect(page.locator(".main-footer")).toContainText(current);
  await expect(page.locator(".dossier-view h1")).toContainText("Transformer");
  await expect(page.getByRole("alert")).toHaveCount(0);
  await page.goto("/#dossier=C01&release=9.9.9-missing");
  await expect(page.getByRole("alert")).toContainText(
    "Unknown release snapshot",
  );
  await page.goto("/#dossier=C01&release=" + current);
  await expect(page.locator(".main-footer")).toContainText(current);
  await expect(page.getByRole("alert")).toHaveCount(0);
});
