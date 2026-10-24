import type { ProblemError } from "@/lib/api/problem";

/** What to tell the person about a problem: one sentence, and sometimes a second line. */
export type Explained = { message: string; more?: string };

const SPLIT_IT = "Split it into smaller files and upload each one.";

/** Why POST /imports refused the file, in plain words (docs/11-import-export.md §5). */
export function explainUploadProblem(problem: ProblemError): Explained {
  if (problem.status === 400) {
    const expected = problem.body.expected_headers;
    if (Array.isArray(expected)) {
      return {
        message: sentence("The columns don't match the template.", problem),
        more: `Expected columns: ${expected.join(", ")}`,
      };
    }
    return { message: sentence("This file can't be read.", problem) };
  }
  if (problem.status === 413) {
    return { message: `This file is larger than 4 MB. ${SPLIT_IT}` };
  }
  if (problem.status === 415) {
    return {
      message:
        "Only .csv and .xlsx files can be imported. In Excel, save the file as CSV UTF-8 or as an Excel workbook (.xlsx).",
    };
  }
  if (problem.errors.some((error) => error.code === "too_many_rows")) {
    return { message: `This file has more than 10,000 rows. ${SPLIT_IT}` };
  }
  return fallback("Couldn't check the file.", problem);
}

/** "The columns don't match the template. Unknown column 'emial'." */
function sentence(lead: string, problem: ProblemError): string {
  return problem.detail ? `${lead} ${problem.detail}` : lead;
}

function fallback(lead: string, problem: ProblemError): Explained {
  return {
    message: sentence(lead, problem),
    more: problem.requestId
      ? `Try again. If it keeps failing, quote request ID ${problem.requestId}.`
      : "Try again.",
  };
}
