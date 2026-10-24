/**
 * Where server-side code reaches FastAPI. Never sent to the browser, which always calls the
 * relative path /api/v1/... on its own origin.
 *
 * - On Vercel (one project, two services) the `backend` service binding injects BACKEND_URL
 *   at runtime; public /api requests are routed to the backend by vercel.json, not Next.js.
 * - Locally (`make dev`, `make e2e`) API_ORIGIN points at uvicorn, and next.config.ts proxies
 *   /api there.
 */
export const API_ORIGIN = process.env.API_ORIGIN ?? "http://localhost:8000";

/** Read at call time, because bindings resolve at runtime, not at build time. */
export function apiBaseUrl(): string {
  return (
    process.env.BACKEND_URL ?? process.env.API_ORIGIN ?? "http://localhost:8000"
  );
}
