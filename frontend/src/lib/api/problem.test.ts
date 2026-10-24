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

  it("keeps the field errors of a validation problem", async () => {
    const response = problemResponse({
      type: "https://acme.example/problems/validation",
      title: "Validation failed",
      status: 422,
      detail: "1 field is invalid.",
      instance: "/api/v1/employees",
      request_id: "req-456",
      errors: [
        {
          loc: ["body", "email"],
          code: "invalid_format",
          message: "Not an email.",
        },
      ],
    });

    const problem = await toProblem(response);

    expect(problem.errors).toEqual([
      {
        loc: ["body", "email"],
        code: "invalid_format",
        message: "Not an email.",
      },
    ]);
  });

  it("describes an error whose body is not a problem, keeping the request id", async () => {
    const response = new Response("<html>Bad gateway</html>", {
      status: 502,
      statusText: "Bad Gateway",
      headers: { "Content-Type": "text/html", "X-Request-ID": "req-789" },
    });

    const problem = await toProblem(response);

    expect(problem).toMatchObject({
      slug: null,
      type: "about:blank",
      title: "Bad Gateway",
      status: 502,
      detail: null,
      requestId: "req-789",
    });
  });

  it("uses a body that openapi-fetch has already read", async () => {
    const response = problemResponse({
      type: "https://acme.example/problems/version-conflict",
      title: "Version conflict",
      status: 409,
      instance: "/api/v1/employees/42",
      request_id: "req-321",
      current_version: 8,
    });
    const error: unknown = await response.json();

    const problem = await toProblem(response, error);

    expect(problem.slug).toBe("version-conflict");
    expect(problem.body.current_version).toBe(8);
  });
});
