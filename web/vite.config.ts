import { defineConfig, loadEnv } from "vite";
export default defineConfig(({ mode }) => ({
  base: "./",
  build: { outDir: "../web_dist", emptyOutDir: true },
  server: {
    proxy: {
      "/api":
        loadEnv(mode, ".", "PRINCIPIA_").PRINCIPIA_API_TARGET ||
        "http://127.0.0.1:8765",
    },
  },
  preview: {
    proxy: {
      "/api":
        loadEnv(mode, ".", "PRINCIPIA_").PRINCIPIA_API_TARGET ||
        "http://127.0.0.1:8765",
    },
  },
}));
