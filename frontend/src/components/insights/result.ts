import { toProblem } from "@/lib/api/problem";

/** A problem as plain fields, ready for <ErrorState> (a Client Component). */
export type PlainProblem = {
  title: string;
  detail: string | null;
  requestId: string | null;
};

/** One insight call's outcome: its data, or the problem the API answered with. */
export type Result<T> =
  { data: T; problem: null } | { data: null; problem: PlainProblem };

/**
 * Waits for an openapi-fetch call and keeps its problem instead of throwing, so one
 * failed section shows its own error and the rest of the page still renders.
 */
export async function settle<T>(
  call: Promise<{ data?: T; error?: unknown; response: Response }>,
): Promise<Result<T>> {
  const { data, error, response } = await call;
  if (data !== undefined) return { data, problem: null };
  const problem = await toProblem(response, error);
  return {
    data: null,
    problem: {
      title: problem.title,
      detail: problem.detail,
      requestId: problem.requestId,
    },
  };
}
