// @vitest-environment node
import { http, HttpResponse } from "msw";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { makeMe } from "@/test/fixtures";
import { server } from "@/test/msw/server";

import { getMe } from "./me";
import { API_ORIGIN } from "./origin";
import type { components } from "./schema";

type MeResponse = components["schemas"]["MeResponse"];
type Problem = components["schemas"]["Problem"];

vi.mock("next/headers", () => ({ cookies: vi.fn() }));
vi.mock("next/navigation", () => ({
  redirect: vi.fn((url: string) => {
    throw new Error(`redirect to ${url}`);
  }),
}));

const ME_URL = `${API_ORIGIN}/api/v1/auth/me`;

beforeEach(() => {
  const store = { get: () => ({ name: "session", value: "jwt" }) };
  vi.mocked(cookies).mockResolvedValue(
    store as unknown as Awaited<ReturnType<typeof cookies>>,
  );
});

describe("getMe", () => {
  it("returns the signed-in person from GET /auth/me", async () => {
    server.use(
      http.get<never, never, MeResponse>(ME_URL, () =>
        HttpResponse.json(makeMe()),
      ),
    );

    const me = await getMe();

    expect(me.user.full_name).toBe("Hema Iyer");
  });

  it("sends an expired or unknown session to /login", async () => {
    server.use(
      http.get<never, never, Problem>(ME_URL, () =>
        HttpResponse.json(
          {
            type: "https://acme.example/problems/unauthenticated",
            title: "Not authenticated",
            status: 401,
            instance: "/api/v1/auth/me",
          },
          { status: 401 },
        ),
      ),
    );

    await expect(getMe()).rejects.toThrow("redirect to /login");
    expect(redirect).toHaveBeenCalledWith("/login");
  });

  it("throws any other problem for the error page to show", async () => {
    server.use(
      http.get<never, never, Problem>(ME_URL, () =>
        HttpResponse.json(
          {
            type: "about:blank",
            title: "Service Unavailable",
            status: 503,
            instance: "/api/v1/auth/me",
            request_id: "req-503",
          },
          { status: 503 },
        ),
      ),
    );

    await expect(getMe()).rejects.toMatchObject({
      status: 503,
      requestId: "req-503",
    });
    expect(redirect).not.toHaveBeenCalled();
  });
});
