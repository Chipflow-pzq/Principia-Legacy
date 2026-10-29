import { defineConfig } from "@playwright/test";
import base from "./playwright.config";

export default defineConfig(base, {
  testMatch: process.env.PRINCIPIA_PUBLIC_URL ? ["hosting.prefix.ts", "hosting.public.ts"] : "hosting.prefix.ts",
  outputDir: "test-results/hosted",
  // This journey includes multiple full reloads over the production network.
  timeout: process.env.PRINCIPIA_PUBLIC_URL ? 90000 : 30000,
  use: { baseURL: process.env.PRINCIPIA_PUBLIC_URL || "http://127.0.0.1:18766/web/legacy/" },
  expect: { timeout: 15000 },
  webServer: process.env.PRINCIPIA_PUBLIC_URL ? undefined : {
    command: "python3 ../hosting/tests/preview.py",
    url: "http://127.0.0.1:18766/web/legacy/healthz",
    reuseExistingServer: false,
  },
  reporter: [["list"], ["json", { outputFile: "test-results/hosted.json" }]],
});
