import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { server } from "@/test/msw/server";
import { makeMe } from "@/test/fixtures";

import type { components } from "./schema";
import { api } from "./client";

type MeResponse = components["schemas"]["MeResponse"];

describe("browser api client", () => {
  it("calls /api/v1 on the page's own origin and sends the session cookie", async () => {
    let seen: Request | undefined;
    server.use(
      http.get<never, never, MeResponse>("/api/v1/auth/me", ({ request }) => {
        seen = request;
        return HttpResponse.json(makeMe());
      }),
    );

    const { data } = await api.GET("/api/v1/auth/me");

    expect(data?.user.email).toBe("hr@acme.example");
    expect(seen?.url).toBe(`${window.location.origin}/api/v1/auth/me`);
    expect(seen?.credentials).toBe("same-origin");
  });
});
