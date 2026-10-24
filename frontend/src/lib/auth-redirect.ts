/**
 * The sign-in redirect that proxy.ts applies (docs/13-frontend-ux.md §2). It is a UX
 * convenience only: FastAPI checks the session and the permissions on every call.
 */

type RequestInfo = { pathname: string; search: string; hasSession: boolean };

/**
 * Paths that never need a session: the API (FastAPI answers 401 itself; redirecting it
 * would break the login request), the login page, Next's assets, and public files.
 * proxy.ts's `matcher` skips the same paths so the proxy doesn't even run for them.
 */
const PUBLIC_PATH =
  /^\/(?:api(?:\/|$)|login(?:\/|$)|_next\/|favicon\.ico$)|\.[a-z0-9]+$/i;

/** Where to send this request instead, or null to let it through. */
export function loginRedirectFor({
  pathname,
  search,
  hasSession,
}: RequestInfo): string | null {
  if (hasSession || PUBLIC_PATH.test(pathname)) return null;
  return `/login?${new URLSearchParams({ next: pathname + search }).toString()}`;
}

export function safeNextPath(next: string | null): string {
  void next;
  throw new Error("safeNextPath is not implemented yet");
}
