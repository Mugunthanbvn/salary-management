# Frontend (Next.js)

Loaded when working under `frontend/`. Root rules in [../CLAUDE.md](../CLAUDE.md) still apply.

## Stack

Node 22, pnpm (via corepack). Next.js 16 App Router, React 19, TypeScript strict, Tailwind v4, shadcn/ui,
TanStack Table, react-hook-form + zod, nuqs, openapi-fetch + openapi-typescript, sonner.
Quality: ESLint flat config (Next 16 has no `next lint`), Prettier, Vitest + React Testing Library + MSW, Playwright.

## Rules

- **Dependencies:** `pnpm add <pkg>` / `pnpm add -D <pkg>` / `pnpm remove <pkg>`. Never edit `pnpm-lock.yaml`.
- **API types come only from the generated `src/lib/api/schema.d.ts`.** Never hand-write API response types.
  After a backend change run `make api-sync` (it writes `openapi.json` and `schema.d.ts`; both are generated).
- **Data fetching:** Server Components call the API with the typed openapi-fetch client in `src/lib/api/`,
  sending `Authorization: Bearer <JWT>` (from the `session` cookie) to `API_ORIGIN`.
  Mutations use Server Actions, then `revalidatePath`. Client fetching only where interactivity needs it.
- **Cache Components is on** (`cacheComponents` in `next.config.ts`): put uncached fetches and `cookies()` reads
  inside `<Suspense>`; there is no `export const dynamic`. Read `node_modules/next/dist/docs/` before using a Next API.
- **Login and file uploads use a client `fetch` to `/api/v1/...` through the rewrite**, never a Server Action
  (the cookie must reach the browser; Server Actions have a 1 MB body limit).
- **`proxy.ts`** redirects to `/login` without a session cookie (UX only) and excludes `/api` and `/login`.
- **No business logic and no money arithmetic.** FastAPI decides permissions, masking and every figure.
  The UI hides controls by **permission** (from `GET /auth/me`), never by role name.
- **Money:** always format with `lib/money.ts` (`amount_minor` + `currency`, currency exponent, `Intl.NumberFormat`).
  No floats; monthly display is annual ÷ 12, half-even, display only. Every amount shows its currency.
- **Filter, sort and paging state lives in the URL** (nuqs), using the API's parameter names.
- **UI follows [docs/design/DESIGN.md](../docs/design/DESIGN.md)** ("Marked-up printout"); reference screens in
  `docs/design/claude/*.dc.html`. Use existing shadcn components before creating new ones.
- **Fully mobile responsive:** every screen and action works from 360 px; check at 390 × 844 and 1440 × 900.
  Tables become list rows on phones; touch targets ≥ 44 px; no horizontal page scroll.
- **Accessibility:** a label on every input, keyboard-reachable actions, visible focus, errors linked
  with `aria-describedby`, flags never by colour alone.

## Tests

- Vitest + RTL for components and utils (`*.test.ts(x)` next to the code). Test what the user sees.
- MSW handlers typed from the generated types.
- Playwright (`e2e/`): one smoke flow (HR login → search → record raise) at 1440 px and 390 px.
- While iterating: `pnpm vitest <file>`. Before done: `make verify` from the repo root.
