import { describe, expect, it } from "vitest";

import { makeProblem, makeValidationProblem } from "@/test/fixtures";

import { fieldErrors, toPlainProblem } from "./action-result";
import { ProblemError } from "./problem";

describe("toPlainProblem", () => {
  it("keeps what a form shows: slug, title, detail, field errors, request id", () => {
    const problem = new ProblemError(
      makeValidationProblem([
        {
          loc: ["body", "base_minor"],
          code: "greater_than",
          message: "Too low",
        },
      ]),
    );

    expect(toPlainProblem(problem)).toEqual({
      slug: "validation",
      title: "Validation failed",
      status: 422,
      detail: "1 fields are invalid.",
      errors: [
        {
          loc: ["body", "base_minor"],
          code: "greater_than",
          message: "Too low",
        },
      ],
      requestId: "req-422",
      currentVersion: null,
    });
  });

  it("keeps the current version of a version conflict", () => {
    const problem = new ProblemError(
      makeProblem("version-conflict", 409, { current_version: 8 }),
    );

    expect(toPlainProblem(problem).currentVersion).toBe(8);
  });

  it("is plain data, so a Server Action can return it", () => {
    const problem = new ProblemError(makeProblem("duplicate", 409));

    const plain = toPlainProblem(problem);

    expect(structuredClone(plain)).toEqual(plain);
    expect(plain).not.toBeInstanceOf(Error);
  });
});

describe("fieldErrors", () => {
  it("names each field error by its place in the request body", () => {
    const problem = toPlainProblem(
      new ProblemError(
        makeValidationProblem([
          {
            loc: ["body", "effective_date"],
            code: "future_date",
            message: "A",
          },
          {
            loc: ["body", "components", 1, "amount_minor"],
            code: "less_than_equal",
            message: "B",
          },
          {
            loc: ["body", "salary", "base_minor"],
            code: "greater_than",
            message: "C",
          },
        ]),
      ),
    );

    expect(fieldErrors(problem)).toEqual({
      effective_date: "A",
      "components.1.amount_minor": "B",
      "salary.base_minor": "C",
    });
  });

  it("joins two messages for the same field", () => {
    const problem = toPlainProblem(
      new ProblemError(
        makeValidationProblem([
          { loc: ["body", "email"], code: "a", message: "Not an email." },
          { loc: ["body", "email"], code: "b", message: "Too long." },
        ]),
      ),
    );

    expect(fieldErrors(problem)).toEqual({ email: "Not an email. Too long." });
  });

  it("is empty without a problem", () => {
    expect(fieldErrors(null)).toEqual({});
  });
});
