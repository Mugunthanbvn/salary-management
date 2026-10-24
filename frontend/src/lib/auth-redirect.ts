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
  return loginPath(pathname + search);
}

/** /login, with the page to come back to after signing in when there is one. */
export function loginPath(next: string | null): string {
  return next ? `/login?${new URLSearchParams({ next }).toString()}` : "/login";
}

/**
 * Request header proxy.ts sets to the page's path and query. Server Components can't read
 * the URL, and getMe() needs it to send an expired session to /login?next=<page>.
 */
export const PAGE_HEADER = "x-pathname";

/** The page's path and query, without Next's internal `_rsc` parameter. */
export function pageOf(url: URL): { pathname: string; search: string } {
  const params = new URLSearchParams(url.search);
  params.delete("_rsc");
  const query = params.toString();
  return { pathname: url.pathname, search: query ? `?${query}` : "" };
}

export const AFTER_LOGIN_PATH = "/insights";

/**
 * The `next` page to open after signing in: a path on this site ("/…"), or /insights.
 * "//host" and "/\\host" are refused: browsers read both as another site. So is any
 * whitespace or control character, which browsers drop ("/<tab>/host" is "//host").
 */
export function safeNextPath(next: string | null): string {
  if (!next || !next.startsWith("/")) return AFTER_LOGIN_PATH;
  if (/[\s\p{Cc}]/u.test(next)) return AFTER_LOGIN_PATH;
  if (next.startsWith("//") || next.startsWith("/\\")) return AFTER_LOGIN_PATH;
  return next;
}
