// @vitest-environment node
import { unstable_doesMiddlewareMatch } from "next/experimental/testing/server";
import { describe, expect, it } from "vitest";

import { config } from "./proxy";

describe("proxy matcher", () => {
  it.each(["/", "/insights", "/insights/pay-equity", "/employees/42", "/ask"])(
    "runs for the page %s",
    (url) => {
      expect(unstable_doesMiddlewareMatch({ config, url })).toBe(true);
    },
  );

  // The login request must reach FastAPI, and assets carry no data.
  it.each([
    "/api/v1/auth/login",
    "/api/v1/employees",
    "/login",
    "/_next/static/chunks/app.js",
    "/_next/image",
    "/favicon.ico",
    "/acme-logo.svg",
  ])("skips %s", (url) => {
    expect(unstable_doesMiddlewareMatch({ config, url })).toBe(false);
  });
});
