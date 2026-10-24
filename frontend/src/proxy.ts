import { NextResponse, type NextRequest } from "next/server";

import { loginRedirectFor } from "@/lib/auth-redirect";
import { SESSION_COOKIE } from "@/lib/session-cookie";

/**
 * Next 16's middleware: without a `session` cookie, go to /login?next=<page>.
 * UX only. It can't tell a valid session from an expired one; the (app) layout asks
 * GET /auth/me and FastAPI enforces every permission (docs/13-frontend-ux.md §2).
 */
export function proxy(request: NextRequest) {
  const target = loginRedirectFor({
    pathname: request.nextUrl.pathname,
    search: request.nextUrl.search,
    hasSession: request.cookies.has(SESSION_COOKIE),
  });
  return target
    ? NextResponse.redirect(new URL(target, request.url))
    : NextResponse.next();
}

export const config = {
  // Don't run for the API (the login request must reach FastAPI), the login page, Next's
  // assets or public files. loginRedirectFor() repeats these rules and is unit-tested.
  matcher: ["/((?!api/|api$|_next/|login|favicon\\.ico|.*\\.[a-zA-Z0-9]+$).*)"],
};
