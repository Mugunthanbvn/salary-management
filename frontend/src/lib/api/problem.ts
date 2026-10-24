export class ProblemError extends Error {}

export function toProblem(response: Response): Promise<ProblemError> {
  void response;
  throw new Error("toProblem is not implemented yet");
}
