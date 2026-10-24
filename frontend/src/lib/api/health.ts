export type ApiHealth = "ok";

/** Calls `GET /api/v1/health` on the API, server-side, and never caches the answer. */
export async function getApiHealth(apiOrigin: string): Promise<ApiHealth> {
  await fetch(`${apiOrigin}/api/v1/health`, { cache: "no-store" });
  return "ok";
}
