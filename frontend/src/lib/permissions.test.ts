import { describe, expect, it } from "vitest";

import { makeMe, VIEWER_PERMISSIONS } from "@/test/fixtures";

import { can, canAsk } from "./permissions";

describe("can", () => {
  it("is true for a permission the person has", () => {
    expect(can(makeMe(), "IMPORT")).toBe(true);
  });

  it("is false for a permission the person lacks", () => {
    const viewer = makeMe({ permissions: VIEWER_PERMISSIONS });

    expect(can(viewer, "IMPORT")).toBe(false);
  });

  it("reads the permissions, never the role name", () => {
    const admin = makeMe({
      user: {
        id: 1,
        email: "admin@acme.example",
        full_name: "Arun",
        role: "ADMIN",
      },
      permissions: [],
    });

    expect(can(admin, "IMPORT")).toBe(false);
  });
});

describe("canAsk", () => {
  it.each([
    { ask: true, permission: true, shown: true },
    { ask: false, permission: true, shown: false },
    { ask: true, permission: false, shown: false },
  ])(
    "is $shown when the feature is on: $ask and the ASK permission is held: $permission",
    ({ ask, permission, shown }) => {
      const me = makeMe({
        features: { ask },
        permissions: permission ? ["INSIGHTS_READ", "ASK"] : ["INSIGHTS_READ"],
      });

      expect(canAsk(me)).toBe(shown);
    },
  );
});
