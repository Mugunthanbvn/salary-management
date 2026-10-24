// @vitest-environment node
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { makeProblem, makeReference } from "@/test/fixtures";
import { server } from "@/test/msw/server";
import { signedInRequest } from "@/test/server";

import { API_ORIGIN } from "./origin";
import { ProblemError } from "./problem";
import { getReference } from "./reference";
import type { components } from "./schema";

type ReferenceData = components["schemas"]["ReferenceData"];
type Problem = components["schemas"]["Problem"];

vi.mock("next/headers", () => ({ cookies: vi.fn() }));

const REFERENCE_URL = `${API_ORIGIN}/api/v1/reference`;

describe("getReference", () => {
  it("reads every dropdown value from GET /reference as the signed-in person", async () => {
    signedInRequest("jwt-hr");
    let authorization: string | null = null;
    server.use(
      http.get<never, never, ReferenceData>(REFERENCE_URL, ({ request }) => {
        authorization = request.headers.get("Authorization");
        return HttpResponse.json(makeReference());
      }),
    );

    const reference = await getReference();

    expect(reference.currencies).toContainEqual({ code: "JPY", exponent: 0 });
    expect(authorization).toBe("Bearer jwt-hr");
  });

  it("throws the API's problem, with its request id, when it fails", async () => {
    signedInRequest();
    server.use(
      http.get<never, never, Problem>(REFERENCE_URL, () =>
        HttpResponse.json(
          makeProblem("not-found", 503, {
            type: "about:blank",
            title: "Service Unavailable",
            request_id: "req-503",
          }),
          { status: 503 },
        ),
      ),
    );

    const failure = getReference();

    await expect(failure).rejects.toBeInstanceOf(ProblemError);
    await expect(failure).rejects.toMatchObject({
      status: 503,
      requestId: "req-503",
    });
  });
});
