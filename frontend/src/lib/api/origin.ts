/**
 * Base URL of the FastAPI app, for server-side code only: the /api rewrite in next.config.ts
 * and fetches from Server Components. It has no NEXT_PUBLIC_ prefix, so it is never sent to
 * the browser, which always calls the relative path /api/v1/...
 */
export const API_ORIGIN = process.env.API_ORIGIN ?? "http://localhost:8000";
