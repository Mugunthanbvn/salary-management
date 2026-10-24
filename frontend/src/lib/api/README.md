# API client

`schema.d.ts` holds the TypeScript types generated from the FastAPI OpenAPI spec by `make api-sync` (it writes
`frontend/openapi.json`, then runs `pnpm api:types`). Both generated files are never edited by hand. API types
come only from `schema.d.ts` (`components["schemas"]["MeResponse"]`, `paths`).

| Module       | Where                             | What                                                                                                                                                                              |
| ------------ | --------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `server.ts`  | Server Components, Server Actions | `const api = await serverApi()`: calls `API_ORIGIN` with `Authorization: Bearer <JWT>` from the `session` cookie, never cached. Reads `cookies()`, so call it inside `<Suspense>` |
| `client.ts`  | Client Components                 | `api`: calls `/api/v1/...` on the page's own origin through the rewrite, sending the cookie. Use it for login, logout, uploads and Ask, never a Server Action                     |
| `me.ts`      | Server Components                 | `getMe()`: the signed-in person (`GET /auth/me`), cached per request; 401 → `/login?next=<page>` (page from proxy.ts's `x-pathname` header), other problems throw                 |
| `problem.ts` | anywhere                          | `toProblem(response, error)` → `ProblemError` with `slug`, `title`, `status`, `detail`, `errors`, `requestId`, `body`                                                             |
| `origin.ts`  | server and config                 | `API_ORIGIN`, never sent to the browser                                                                                                                                           |
| `health.ts`  | server                            | `getApiHealth()`: is the API up (B1)                                                                                                                                              |

```ts
const api = await serverApi();
const { data, error, response } = await api.GET("/api/v1/auth/me");
if (error) throw await toProblem(response, error);
```

In a Server Component, prefer rendering `<ErrorState title={p.title} detail={p.detail} requestId={p.requestId} />`
over throwing: in production Next only sends the browser a generic message for thrown server errors.

Tests: MSW handlers typed from the schema (`http.get<never, never, MeResponse>(...)`); fixtures in
`src/test/fixtures.ts` (`makeMe()`, permission sets).
