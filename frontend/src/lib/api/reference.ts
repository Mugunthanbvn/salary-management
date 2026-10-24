import "server-only";

import { cache } from "react";

import { toProblem } from "./problem";
import type { components } from "./schema";
import { serverApi } from "./server";

type ReferenceData = components["schemas"]["ReferenceData"];

/**
 * Every dropdown value and the currency exponents (GET /reference), for Server Components.
 * Fetched once per page load (React cache), as the signed-in person; a problem is thrown.
 * It reads cookies(), so call it inside a <Suspense> boundary.
 */
export const getReference = cache(async (): Promise<ReferenceData> => {
  const api = await serverApi();
  const { data, error, response } = await api.GET("/api/v1/reference");
  if (data) return data;
  throw await toProblem(response, error);
});
