import "server-only";

import { redirect } from "next/navigation";
import { cache } from "react";

import type { Me } from "@/lib/permissions";

import { toProblem } from "./problem";
import { serverApi } from "./server";

/**
 * The signed-in person (GET /api/v1/auth/me), for Server Components.
 *
 * The (app) layout calls it to render the shell; a page may call it again to check a
 * permission, and React's cache() makes that one request per page load. A missing or
 * expired session (401) goes to /login; any other problem is thrown as a ProblemError.
 * It reads cookies(), so call it inside a <Suspense> boundary.
 */
export const getMe = cache(async (): Promise<Me> => {
  const api = await serverApi();
  const { data, error, response } = await api.GET("/api/v1/auth/me");
  if (data) return data;
  if (response.status === 401) redirect("/login");
  throw await toProblem(response, error);
});
