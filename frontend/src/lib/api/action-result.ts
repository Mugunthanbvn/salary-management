import type { ProblemError } from "./problem";
import type { components } from "./schema";

type FieldError = components["schemas"]["FieldError"];

export type PlainProblem = {
  slug: string | null;
  title: string;
  status: number;
  detail: string | null;
  errors: FieldError[];
  requestId: string | null;
  currentVersion: number | null;
};

export function toPlainProblem(problem: ProblemError): PlainProblem {
  void problem;
  throw new Error("toPlainProblem is not implemented yet");
}

export function fieldErrors(
  problem: PlainProblem | null,
): Record<string, string> {
  void problem;
  throw new Error("fieldErrors is not implemented yet");
}
