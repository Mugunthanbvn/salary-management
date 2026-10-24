import { defineConfig, devices } from "@playwright/test";

// Fixed ports away from `make dev` (3000 / 8000), so a running dev stack never interferes.
const PORT = 3100;
const BASE_URL = `http://localhost:${PORT}`;
const API_PORT = 8100;
const API_ORIGIN = `http://127.0.0.1:${API_PORT}`;
const isCI = Boolean(process.env.CI);

// Every screen must work on a phone, so each test runs at desktop and phone size
// (docs/14-testing-strategy.md §5.8). Both use Chromium, the browser installed for CI.
export default defineConfig({
  testDir: "e2e",
  fullyParallel: true,
  forbidOnly: isCI,
  retries: isCI ? 1 : 0,
  reporter: isCI ? [["github"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: BASE_URL,
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "desktop",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1440, height: 900 },
      },
    },
    {
      name: "phone",
      use: {
        ...devices["Pixel 7"],
        viewport: { width: 390, height: 844 },
        isMobile: true,
        hasTouch: true,
      },
    },
  ],
  // A real local stack, started fresh for every run and stopped after it: the API on a new
  // temp SQLite file with a small deterministic seed (e2e/start-api.sh), and the production
  // build of the web app. API_ORIGIN is read at build time (the /api rewrite), so it is set
  // for `next build` too.
  webServer: [
    {
      command: "bash e2e/start-api.sh",
      url: `${API_ORIGIN}/api/v1/health`,
      env: { E2E_API_PORT: String(API_PORT) },
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: `pnpm build && pnpm start -p ${PORT}`,
      url: BASE_URL,
      env: { API_ORIGIN },
      reuseExistingServer: false,
      timeout: 300_000,
    },
  ],
});
