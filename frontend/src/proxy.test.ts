// @vitest-environment node
import { unstable_doesMiddlewareMatch } from "next/experimental/testing/server";
import { NextRequest } from "next/server";
import { describe, expect, it } from "vitest";

import { config, proxy } from "./proxy";

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

describe("proxy", () => {
  function request(url: string, cookie?: string) {
    return new NextRequest(url, { headers: cookie ? { cookie } : {} });
  }

  it("sends a visitor without a session to /login?next=<page>", () => {
    const response = proxy(request("http://acme.test/employees?country=DE"));

    expect(response.headers.get("location")).toBe(
      "http://acme.test/login?next=%2Femployees%3Fcountry%3DDE",
    );
  });

  // Server Components can't read the URL; getMe needs it for /login?next= when the
  // cookie is there but the session has expired. Next's own _rsc parameter is left out.
  it.each([
    "http://acme.test/employees?country=DE",
    "http://acme.test/employees?country=DE&_rsc=1x2y3",
  ])("passes the page on to the server as x-pathname (%s)", (url) => {
    const response = proxy(request(url, "session=jwt"));

    expect(response.headers.get("x-middleware-request-x-pathname")).toBe(
      "/employees?country=DE",
    );
  });
});
