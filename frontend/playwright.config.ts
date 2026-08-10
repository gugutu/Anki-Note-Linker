import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "tests/browser",
  fullyParallel: false,
  workers: 1,
  forbidOnly: Boolean(process.env.CI),
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : "list",
  use: {
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
});
