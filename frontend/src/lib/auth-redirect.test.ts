import { describe, expect, it } from "vitest";

import { loginRedirectFor } from "./auth-redirect";

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
