import { defineConfig, devices } from "@playwright/test";
export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  workers: 1,
  timeout: 30000,
  use: {
    baseURL: process.env.PRINCIPIA_TEST_URL || "http://127.0.0.1:8765",
    headless: true,
    channel: "chrome",
    viewport: { width: 1440, height: 1000 },
  },
  projects: [
    {
      name: "desktop",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1440, height: 1000 },
      },
    },
    {
      name: "mobile",
      use: { ...devices["iPhone 13"], defaultBrowserType: "chromium" },
    },
  ],
  reporter: [["list"], ["json", { outputFile: "test-results/results.json" }]],
});
