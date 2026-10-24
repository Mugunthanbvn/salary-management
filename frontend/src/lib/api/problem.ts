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

/**
 * Reads the problem+json body of an error response. A body that is not a problem (for
 * example an HTML 502 from a proxy) becomes an "about:blank" problem with the status text,
 * keeping the X-Request-ID header when there is one.
 */
export async function toProblem(
  response: Response,
  parsedBody?: unknown,
): Promise<ProblemError> {
  void parsedBody;
  const body = await readJson(response);
  const requestId = response.headers.get("X-Request-ID");
  if (isProblem(body)) {
    return new ProblemError({
      ...body,
      request_id: body.request_id ?? requestId,
    });
  }
  return new ProblemError({
    type: "about:blank",
    title: response.statusText || "Something went wrong",
    status: response.status,
    detail: null,
    instance: "",
    request_id: requestId,
  });
}

async function readJson(response: Response): Promise<unknown> {
  try {
    return JSON.parse(await response.text());
  } catch {
    return undefined;
  }
}

function isProblem(body: unknown): body is Problem {
  if (typeof body !== "object" || body === null) return false;
  const { type, title, status } = body as Record<string, unknown>;
  return (
    typeof type === "string" &&
    typeof title === "string" &&
    typeof status === "number"
  );
}
