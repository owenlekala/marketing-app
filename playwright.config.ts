import { defineConfig, devices } from "@playwright/test";
import { baseURL } from "./tests/browser/target";

export default defineConfig({
  testDir: "./tests/browser",
  testMatch: process.env.WA_NEGATIVE_NETWORK_PROBE ? "**/*.probe.ts" : "**/*.spec.ts",
  outputDir: process.env.WA_TEST_OUTPUT || ".local/test-results/browser",
  workers: 1,
  retries: 0,
  maxFailures: 1,
  timeout: 60_000,
  reporter: "list",
  use: {
    baseURL,
    serviceWorkers: "block",
    trace: "off",
    video: "off",
    screenshot: "only-on-failure"
  },
  projects: [
    { name: "desktop-light", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 1000 }, colorScheme: "light" } },
    { name: "desktop-dark", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 1000 }, colorScheme: "dark" } },
    { name: "tablet", use: { ...devices["Desktop Chrome"], viewport: { width: 1024, height: 768 }, colorScheme: "light" } },
    { name: "mobile", use: { ...devices["Desktop Chrome"], viewport: { width: 390, height: 844 }, colorScheme: "light" } }
  ]
});
