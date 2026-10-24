import { NextResponse, type NextRequest } from "next/server";

import { loginRedirectFor, PAGE_HEADER, pageOf } from "@/lib/auth-redirect";
import { SESSION_COOKIE } from "@/lib/session-cookie";

/**
 * Next 16's middleware: without a `session` cookie, go to /login?next=<page>; with one,
 * pass the page on to Server Components in the x-pathname request header.
 * UX only. It can't tell a valid session from an expired one; the (app) layout asks
 * GET /auth/me and FastAPI enforces every permission (docs/13-frontend-ux.md §2).
 */
export function proxy(request: NextRequest) {
  const page = pageOf(request.nextUrl);
  const target = loginRedirectFor({
    ...page,
    hasSession: request.cookies.has(SESSION_COOKIE),
  });
  if (target) return NextResponse.redirect(new URL(target, request.url));
  // Tell Server Components which page this is (it replaces any value the browser sent).
  const headers = new Headers(request.headers);
  headers.set(PAGE_HEADER, page.pathname + page.search);
  return NextResponse.next({ request: { headers } });
}

export const config = {
  // Don't run for the API (the login request must reach FastAPI), the login page, Next's
  // assets or public files. loginRedirectFor() repeats these rules and is unit-tested.
  matcher: ["/((?!api/|api$|_next/|login|favicon\\.ico|.*\\.[a-zA-Z0-9]+$).*)"],
};
