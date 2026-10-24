// @vitest-environment node
import { describe, expect, it, vi } from "vitest";

// next.config.ts reads API_ORIGIN when it loads, so load a fresh copy per test.
async function loadRewrites() {
  vi.resetModules();
  const { default: nextConfig } = await import("./next.config");
  return nextConfig.rewrites?.();
}

describe("next.config rewrites", () => {
  it("proxies /api to API_ORIGIN, so the browser stays on one origin", async () => {
    vi.stubEnv("API_ORIGIN", "https://api.example.test");

    const rewrites = await loadRewrites();

    expect(rewrites).toEqual([
      {
        source: "/api/:path*",
        destination: "https://api.example.test/api/:path*",
      },
    ]);
  });

  it("proxies /api to the local API on port 8000 when API_ORIGIN is not set", async () => {
    vi.stubEnv("API_ORIGIN", undefined);

    const rewrites = await loadRewrites();

    expect(rewrites).toEqual([
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/api/:path*",
      },
    ]);
  });
});

describe("next.config redirects", () => {
  it("sends / to /insights, the landing page", async () => {
    const { default: nextConfig } = await import("./next.config");

    const redirects = await nextConfig.redirects?.();

    expect(redirects).toEqual([
      { source: "/", destination: "/insights", permanent: false },
    ]);
  });
});
