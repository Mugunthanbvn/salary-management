import createClient from "openapi-fetch";

import type { paths } from "./schema";

/**
 * The typed API client for Client Components (login, logout, uploads, Ask).
 *
 * It calls `/api/v1/...` on the page's own origin, and the Next.js rewrite forwards the
 * request to FastAPI, so the httpOnly `session` cookie is first-party and sent as is
 * (docs/05-architecture.md §4.3). It never uses API_ORIGIN, which the browser doesn't know.
 * Server Components use `serverApi()` from `./server` instead.
 *
 *   const { data, error, response } = await api.POST("/api/v1/auth/logout");
 *   if (error) throw await toProblem(response, error);
 */
export const api = createClient<paths>({
  // A relative URL works in the browser; jsdom tests need the origin spelled out.
  baseUrl: typeof window === "undefined" ? "" : window.location.origin,
  credentials: "same-origin",
  // Look fetch up on each call, so test doubles (MSW) installed later are used.
  fetch: (request: Request) => globalThis.fetch(request),
});
