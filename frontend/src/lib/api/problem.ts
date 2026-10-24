import type { components } from "./schema";

type Problem = components["schemas"]["Problem"];
type FieldError = components["schemas"]["FieldError"];

const PROBLEM_TYPE_PREFIX = "https://acme.example/problems/";

/**
 * An API error as an Error you can throw or show: the RFC 9457 problem+json body
 * (docs/07-api-spec.md §1.5) with its glossary §5 slug, field errors and request id.
 */
export class ProblemError extends Error {
  /** The glossary §5 slug, e.g. "version-conflict"; null for "about:blank" problems. */
  readonly slug: string | null;
  readonly type: string;
  readonly title: string;
  readonly status: number;
  readonly detail: string | null;
  /** Field errors of a 422 `validation` problem; empty otherwise. */
  readonly errors: FieldError[];
  /** Quote this to support; it matches the API's logs. */
  readonly requestId: string | null;
  /** The whole body, for members a problem adds (e.g. `current_version`). */
  readonly body: Problem;

  constructor(body: Problem) {
    super(body.detail ?? body.title);
    this.name = "ProblemError";
    this.body = body;
    this.type = body.type;
    this.slug = body.type.startsWith(PROBLEM_TYPE_PREFIX)
      ? body.type.slice(PROBLEM_TYPE_PREFIX.length)
      : null;
    this.title = body.title;
    this.status = body.status;
    this.detail = body.detail ?? null;
    this.errors = Array.isArray(body.errors)
      ? (body.errors as FieldError[])
      : [];
    this.requestId = body.request_id ?? null;
  }
}

/** Reads the problem+json body of an error response. */
export async function toProblem(response: Response): Promise<ProblemError> {
  const body = (await response.json()) as Problem;
  return new ProblemError(body);
}
