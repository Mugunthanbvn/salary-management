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

  it("adds no /api proxy when API_ORIGIN is not set (Vercel routes /api to the backend service)", async () => {
    vi.stubEnv("API_ORIGIN", undefined);

    const rewrites = await loadRewrites();

    expect(rewrites).toEqual([]);
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
