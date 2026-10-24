import { cookies } from "next/headers";
import { vi } from "vitest";

type CookieStore = Awaited<ReturnType<typeof cookies>>;

/**
 * For tests of server code that calls serverApi(): the incoming request carries a
 * `session` cookie. The test file must `vi.mock("next/headers", ...)` with a `cookies` spy.
 */
export function signedInRequest(jwt = "jwt-from-cookie"): void {
  const store = {
    get: (name: string) =>
      name === "session" ? { name, value: jwt } : undefined,
  };
  vi.mocked(cookies).mockResolvedValue(store as unknown as CookieStore);
}
