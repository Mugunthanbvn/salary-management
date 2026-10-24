import "server-only";

import { headers } from "next/headers";
import { redirect } from "next/navigation";
import { cache } from "react";

import { loginPath, PAGE_HEADER } from "@/lib/auth-redirect";
import type { Me } from "@/lib/permissions";

import { toProblem } from "./problem";
import { serverApi } from "./server";

/**
 * The signed-in person (GET /api/v1/auth/me), for Server Components.
 *
 * The (app) layout calls it to render the shell; a page may call it again to check a
 * permission, and React's cache() makes that one request per page load. A missing or
 * expired session (401) goes to /login?next=<page> (proxy.ts passes the page in the
 * x-pathname header); any other problem is thrown as a ProblemError.
 * It reads cookies() and headers(), so call it inside a <Suspense> boundary.
 */
export const getMe = cache(async (): Promise<Me> => {
  const api = await serverApi();
  const { data, error, response } = await api.GET("/api/v1/auth/me");
  if (data) return data;
  if (response.status === 401) {
    // The cookie is there but the session has expired: come back to this page afterwards.
    redirect(loginPath((await headers()).get(PAGE_HEADER)));
  }
  throw await toProblem(response, error);
});
