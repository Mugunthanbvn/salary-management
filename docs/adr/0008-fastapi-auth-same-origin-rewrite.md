# ADR-0008: FastAPI owns authentication; same origin through a Next.js `rewrites` rule

- **Status:** Accepted
- **Date:** 2026-10-24
- **Deciders:** the candidate + Claude (AI pair)

## Context

The app exposes confidential salary data on a public URL, so real authentication and role-based access are required (see [ADR-0009](0009-permission-rbac-small-group-rule.md)). The candidate initially asked for "full auth (Auth.js + roles)". Research showed:

- **Auth.js (NextAuth v5) is in maintenance / security-patch mode.** The Better Auth team took over maintenance in September 2025 and points new projects to Better Auth.
- Auth.js and Better Auth both want to own users and sessions **inside the Node/Next.js process**. Our API and source of truth for roles is **FastAPI**.
- Deployment is two Vercel projects (web + API). `*.vercel.app` is on the **Public Suffix List**, so `app-x.vercel.app` and `api-y.vercel.app` are **different sites**. A cookie set by the API and sent from the web origin would be a **third-party cookie**, which Safari (ITP) and Firefox block by default.

The candidate asked "why do we need a BFF?", then "what are the other methods?". All alternatives below were discussed.

## Decision drivers

- One authority for identity and permissions, testable in pytest.
- The token must not be readable by JavaScript (XSS resilience).
- Must work in Safari and Firefox, since reviewers may use a Mac.
- Server-side rendering of logged-in data must keep working.
- $0, no extra service to run.

## Considered options

1. **FastAPI-owned auth + a same-origin `rewrites` rule in Next.js** (`/api/:path*` → API project).
2. **Auth.js v5 Credentials provider** wrapping a FastAPI-issued JWT.
3. **Better Auth in Next.js + FastAPI verifying JWTs via JWKS.**
4. **Bearer token in the browser** (localStorage or memory) + CORS.
5. **Cross-site cookie** (`SameSite=None; Secure`) + CORS with credentials + CSRF token (optionally CHIPS partitioned cookies).
6. **Shared custom parent domain** (`app.example.dev` + `api.example.dev`).
7. **FastAPI serving a Next.js static export** (single origin).
8. **Hosted auth provider** (Clerk/Auth0 free tier) + JWKS verification in FastAPI.

### Option 2: Auth.js v5
- Pros: familiar; the candidate's original pick.
- Cons: the library is security-patch-only; it adds a second session layer on top of FastAPI's JWT; an interviewer is likely to question choosing a deprecated library for a new build.

### Option 3: Better Auth + JWKS
- Pros: modern and actively maintained.
- Cons: identity is split across two services (users in Node, permissions in Python); more moving parts to explain and test.

### Option 4: Bearer token in the browser
- Pros: simplest SPA pattern; no cookie problems.
- Cons: any XSS can steal a token from localStorage. An in-memory token is lost on refresh and needs a refresh cookie, which brings back the cross-site problem. Server Components can't fetch logged-in data, so everything becomes client-side.

### Option 5: Cross-site cookie
- Pros: the cookie stays httpOnly.
- Cons: blocked by default in Safari and Firefox, so the demo may not even log in for a reviewer. CHIPS partitioned-cookie support is uneven. Too fragile.

### Option 6: Shared custom domain
- Pros: the cleanest production setup; first-party `SameSite=Lax` cookie with no proxy.
- Cons: needs a paid domain (about $1–10/yr) and DNS setup, which breaks the $0 constraint.

### Option 7: FastAPI serves a static export
- Pros: one origin, one deploy.
- Cons: a static export loses Server Components, Server Actions, middleware and SSR, which mostly defeats the reason for choosing Next.js.

### Option 8: Hosted auth provider
- Pros: login, MFA and resets for free.
- Cons: roles live in a third-party service; hides the engineering the assessment wants to see; reviewers depend on another vendor.

## Decision

**Option 1.**

**Backend (source of truth):**
- `users` table with **Argon2** hashes (`pwdlib[argon2]`) and JWTs via **PyJWT** (FastAPI's docs moved off passlib and python-jose).
- `POST /api/v1/auth/login` sets the JWT in an **httpOnly, Secure, `SameSite=Lax`** cookie. `POST /auth/logout` clears it; `GET /auth/me` returns the user and their permissions.
- Authorization through FastAPI dependencies `current_user` and `require_permission(...)` (see [ADR-0009](0009-permission-rbac-small-group-rule.md)).
- Production refuses to start with default secrets.

**Frontend (thin, no business logic):**
- `next.config.ts` rewrites `/api/:path*` → `${API_ORIGIN}/api/:path*`. The browser only ever talks to the web origin, so the cookie is **first-party**.
- Server Components and Server Actions call `API_ORIGIN` directly from the server, forwarding the incoming cookie, so SSR works with logged-in data.
- `proxy.ts` (the Next 16 rename of middleware) redirects unauthenticated users to `/login`. It's a UX convenience only; FastAPI enforces access.

This is **not a separate BFF service**: one config rule plus a small server-side fetch helper.

## Consequences

### Positive
- Token never exposed to JS. CSRF is mitigated by `SameSite=Lax` (mutations are non-GET). Works in all major browsers.
- One identity and permission model, fully covered by pytest authz-matrix tests.
- No deprecated dependency, no extra service, $0.

### Negative / risks
- Every API call goes through Vercel's rewrite proxy, adding a little latency. Acceptable, and measured in the deploy spike.
- No SSO/MFA or password reset flows (out of scope, documented).
- The cookie and rewrite combination must be verified in Safari during the day-1 deploy spike (see [17-deployment.md](../17-deployment.md)).

## Links

- [05-architecture.md](../05-architecture.md), [08-security-rbac.md](../08-security-rbac.md), [17-deployment.md](../17-deployment.md), [20-trade-offs.md](../20-trade-offs.md)
