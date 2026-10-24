export type ApiHealth = "ok" | "unreachable";

/** How long the health check waits for the API before calling it unreachable. */
export const HEALTH_TIMEOUT_MS = 3000;

type HealthOptions = {
  timeoutMs?: number;
};

/**
 * Calls `GET /api/v1/health` on the API, server-side, and never caches the answer.
 * A network error, a timeout, or any non-2xx answer (for example 503 when the database
 * is down) counts as unreachable.
 */
export async function getApiHealth(
  apiOrigin: string,
  { timeoutMs = HEALTH_TIMEOUT_MS }: HealthOptions = {},
): Promise<ApiHealth> {
  try {
    const response = await fetch(`${apiOrigin}/api/v1/health`, {
      cache: "no-store",
      signal: AbortSignal.timeout(timeoutMs),
    });
    return response.ok ? "ok" : "unreachable";
  } catch {
    // Includes the TimeoutError from the abort signal.
    return "unreachable";
  }
}
