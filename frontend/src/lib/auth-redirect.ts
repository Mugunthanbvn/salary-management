/**
 * The sign-in redirect that proxy.ts applies (docs/13-frontend-ux.md §2). It is a UX
 * convenience only: FastAPI checks the session and the permissions on every call.
 */

type RequestInfo = { pathname: string; search: string; hasSession: boolean };

/** Where to send this request instead, or null to let it through. */
export function loginRedirectFor({
  pathname,
  search,
  hasSession,
}: RequestInfo): string | null {
  if (hasSession) return null;
  return `/login?${new URLSearchParams({ next: pathname + search }).toString()}`;
}
