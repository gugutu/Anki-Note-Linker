import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "jsdom",
    include: ["tests/unit/**/*.test.ts"],
    coverage: {
      include: ["src/**/*.ts"],
      provider: "v8",
      reporter: ["text", "json-summary"],
    },
  },
});
