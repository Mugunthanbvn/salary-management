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
});
