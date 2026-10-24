import { describe, expect, it } from "vitest";

import { loginRedirectFor, safeNextPath } from "./auth-redirect";

describe("loginRedirectFor", () => {
  it("sends a visitor without a session to /login, remembering the page", () => {
    const target = loginRedirectFor({
      pathname: "/employees",
      search: "?country=DE&page=2",
      hasSession: false,
    });

    expect(target).toBe("/login?next=%2Femployees%3Fcountry%3DDE%26page%3D2");
  });

  it("lets a visitor with a session through", () => {
    const target = loginRedirectFor({
      pathname: "/insights",
      search: "",
      hasSession: true,
    });

    expect(target).toBeNull();
  });

  // The API answers for itself (401), the login page must stay reachable, and Next's
  // assets and public files carry no data.
  it.each([
    "/login",
    "/api/v1/auth/login",
    "/api/v1/employees",
    "/_next/static/chunks/app.js",
    "/_next/image",
    "/favicon.ico",
    "/acme-logo.svg",
  ])("lets %s through without a session", (pathname) => {
    expect(
      loginRedirectFor({ pathname, search: "", hasSession: false }),
    ).toBeNull();
  });
});

describe("safeNextPath", () => {
  it("keeps a page on this site, with its query", () => {
    expect(safeNextPath("/insights/pay-equity?country=DE")).toBe(
      "/insights/pay-equity?country=DE",
    );
  });

  // Anything else could send a person who just signed in to another site.
  it.each([
    null,
    "",
    "insights",
    "//evil.example/insights",
    "/\\evil.example",
    "https://evil.example",
    "javascript:alert(1)",
    "/\t/evil.example", // browsers drop tabs and newlines: this reads as //evil.example
  ])("falls back to /insights for %j", (next) => {
    expect(safeNextPath(next)).toBe("/insights");
  });
});
