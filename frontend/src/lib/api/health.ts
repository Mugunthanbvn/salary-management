export type ApiHealth = "ok" | "unreachable";

/**
 * Calls `GET /api/v1/health` on the API, server-side, and never caches the answer.
 * A network error, or any non-2xx answer (for example 503 when the database is down),
 * counts as unreachable.
 */
export async function getApiHealth(apiOrigin: string): Promise<ApiHealth> {
  try {
    const response = await fetch(`${apiOrigin}/api/v1/health`, {
      cache: "no-store",
    });
    return response.ok ? "ok" : "unreachable";
  } catch {
    return "unreachable";
  }
}
