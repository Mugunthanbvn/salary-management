import "server-only";

import { cookies } from "next/headers";
import createClient, { type Client } from "openapi-fetch";

import { SESSION_COOKIE } from "@/lib/session-cookie";

import { API_ORIGIN } from "./origin";
import type { paths } from "./schema";

/**
 * The typed API client for Server Components and Server Actions.
 *
 * It calls FastAPI at API_ORIGIN directly (no rewrite hop) and sends the JWT from the
 * incoming `session` cookie as `Authorization: Bearer <JWT>` (docs/17-deployment.md §3.4).
 * Responses are never cached: they depend on who is asking.
 *
 * It reads cookies(), so with Cache Components call it inside a <Suspense> boundary.
 *
 *   const api = await serverApi();
 *   const { data, error, response } = await api.GET("/api/v1/auth/me");
 *   if (error) throw await toProblem(response, error);
 */
export async function serverApi(): Promise<Client<paths>> {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  return createClient<paths>({
    baseUrl: API_ORIGIN,
    cache: "no-store",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    // Look fetch up on each call, so Next's instrumented fetch (and MSW in tests) is used.
    fetch: (request: Request) => globalThis.fetch(request),
  });
}
