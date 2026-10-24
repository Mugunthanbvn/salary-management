// @vitest-environment node
import { http, HttpResponse } from "msw";
import { cookies } from "next/headers";
import { describe, expect, it, vi } from "vitest";

import { makeMe } from "@/test/fixtures";
import { server } from "@/test/msw/server";

import { API_ORIGIN } from "./origin";
import type { components } from "./schema";
import { serverApi } from "./server";

type MeResponse = components["schemas"]["MeResponse"];
type Problem = components["schemas"]["Problem"];

vi.mock("next/headers", () => ({ cookies: vi.fn() }));

type CookieStore = Awaited<ReturnType<typeof cookies>>;

function withCookies(values: Record<string, string>) {
  const store = {
    get: (name: string) =>
      name in values ? { name, value: values[name] } : undefined,
  };
  vi.mocked(cookies).mockResolvedValue(store as unknown as CookieStore);
}

describe("serverApi", () => {
  it("calls API_ORIGIN with the session cookie's JWT as a Bearer token", async () => {
    withCookies({ session: "jwt-from-cookie" });
    let authorization: string | null = null;
    server.use(
      http.get<never, never, MeResponse>(
        `${API_ORIGIN}/api/v1/auth/me`,
        ({ request }) => {
          authorization = request.headers.get("Authorization");
          return HttpResponse.json(makeMe());
        },
      ),
    );

    const api = await serverApi();
    const { data } = await api.GET("/api/v1/auth/me");

    expect(data?.user.email).toBe("hr@acme.example");
    expect(authorization).toBe("Bearer jwt-from-cookie");
  });

  it("calls the backend through the BACKEND_URL service binding when Vercel sets it", async () => {
    vi.stubEnv("BACKEND_URL", "https://backend.internal.test");
    withCookies({ session: "jwt-from-cookie" });
    server.use(
      http.get<never, never, MeResponse>(
        "https://backend.internal.test/api/v1/auth/me",
        () => HttpResponse.json(makeMe()),
      ),
    );

    const api = await serverApi();
    const { data } = await api.GET("/api/v1/auth/me");

    expect(data?.user.email).toBe("hr@acme.example");
    vi.unstubAllEnvs();
  });

  it("sends no Authorization header when there is no session cookie", async () => {
    withCookies({});
    let authorization: string | null = "not called";
    server.use(
      http.get<never, never, Problem>(
        `${API_ORIGIN}/api/v1/auth/me`,
        ({ request }) => {
          authorization = request.headers.get("Authorization");
          return HttpResponse.json(
            {
              type: "https://acme.example/problems/unauthenticated",
              title: "Not authenticated",
              status: 401,
              instance: "/api/v1/auth/me",
            },
            { status: 401 },
          );
        },
      ),
    );

    const api = await serverApi();
    const { response } = await api.GET("/api/v1/auth/me");

    expect(response.status).toBe(401);
    expect(authorization).toBeNull();
  });
});
