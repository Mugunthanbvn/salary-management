/**
 * What a Server Action returns to the form that called it. A thrown error would reach the
 * browser as a generic message in production, so actions return the API's problem as plain
 * data instead (it must survive serialisation: no class instances).
 */
import type { ProblemError } from "./problem";
import type { components } from "./schema";

type FieldError = components["schemas"]["FieldError"];

export type PlainProblem = {
  /** The glossary §5 slug ("version-conflict"), or null for "about:blank". */
  slug: string | null;
  title: string;
  status: number;
  detail: string | null;
  /** Field errors of a 422 `validation` problem. */
  errors: FieldError[];
  requestId: string | null;
  /** The employee's version now, on a 409 `version-conflict`. */
  currentVersion: number | null;
};

export type ActionResult<T> =
  { ok: true; data: T } | { ok: false; problem: PlainProblem };

export function toPlainProblem(problem: ProblemError): PlainProblem {
  const currentVersion = problem.body.current_version;
  return {
    slug: problem.slug,
    title: problem.title,
    status: problem.status,
    detail: problem.detail,
    errors: problem.errors.map(({ loc, code, message }) => ({
      loc,
      code,
      message,
    })),
    requestId: problem.requestId,
    currentVersion: typeof currentVersion === "number" ? currentVersion : null,
  };
}

/**
 * Field errors by where they sit in the request body: `["body", "components", 1,
 * "amount_minor"]` is `"components.1.amount_minor"`. Two messages for one field are joined.
 */
export function fieldErrors(
  problem: PlainProblem | null,
): Record<string, string> {
  const byField: Record<string, string> = {};
  for (const error of problem?.errors ?? []) {
    const [first, ...rest] = error.loc;
    const key = (first === "body" ? rest : error.loc).join(".");
    byField[key] = byField[key]
      ? `${byField[key]} ${error.message}`
      : error.message;
  }
  return byField;
}
