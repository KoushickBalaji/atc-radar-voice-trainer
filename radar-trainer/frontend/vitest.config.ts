import { defineConfig } from "vitest/config";

export default defineConfig({
  server: { fs: { allow: [".", "../data/traffic"] } },
  test: { environment: "jsdom", include: ["tests/**/*.test.{ts,tsx}"], restoreMocks: true },
});
