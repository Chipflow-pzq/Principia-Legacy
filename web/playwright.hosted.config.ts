import { defineConfig } from "@playwright/test";
import base from "./playwright.config";

export default defineConfig(base, {
  testMatch: "hosting.prefix.ts",
  outputDir: "test-results/hosted",
  use: { baseURL: "http://127.0.0.1:18766/web/legacy/" },
  webServer: {
    command: "python3 ../hosting/tests/preview.py",
    url: "http://127.0.0.1:18766/web/legacy/healthz",
    reuseExistingServer: false,
  },
  reporter: [["list"], ["json", { outputFile: "test-results/hosted.json" }]],
});
