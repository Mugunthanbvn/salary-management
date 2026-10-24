import { describe, expect, it } from "vitest";

import type { components } from "./schema";
import { ProblemError, toProblem } from "./problem";

type Problem = components["schemas"]["Problem"];

function problemResponse(body: Problem, init: ResponseInit = {}): Response {
  return new Response(JSON.stringify(body), {
    status: body.status,
    headers: { "Content-Type": "application/problem+json" },
    ...init,
  });
}

describe("toProblem", () => {
  it("reads an RFC 9457 problem from the response body", async () => {
    const response = problemResponse({
      type: "https://acme.example/problems/unauthenticated",
      title: "Not authenticated",
      status: 401,
      detail: "Invalid email or password",
      instance: "/api/v1/auth/login",
      request_id: "req-123",
    });

    const problem = await toProblem(response);

    expect(problem).toBeInstanceOf(ProblemError);
    expect(problem).toMatchObject({
      slug: "unauthenticated",
      title: "Not authenticated",
      status: 401,
      detail: "Invalid email or password",
      requestId: "req-123",
    });
  });
});
