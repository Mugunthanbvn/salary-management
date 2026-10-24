import type { ProblemError } from "@/lib/api/problem";
import type { components } from "@/lib/api/schema";

type ImportRowError = components["schemas"]["ImportRowError"];

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

/** A refused commit: what to say, the rows now in the way, and whether to try again. */
export type CommitProblem = Explained & {
  /** Rows someone added since the check (409 `duplicate`). */
  conflicts: ImportRowError[];
  /** False when trying the same check again can't work: upload the file again instead. */
  retry: boolean;
};

/** Why POST /imports/{id}/commit refused, in plain words (docs/11-import-export.md §5.6). */
export function explainCommitProblem(problem: ProblemError): CommitProblem {
  const final = { conflicts: [], retry: false };
  if (problem.slug === "duplicate") {
    const conflicts = problem.body.conflicts;
    return {
      ...final,
      message:
        "Nothing was imported: some of these people were added after the check.",
      more: "Remove or fix these rows in your spreadsheet, then upload it again.",
      conflicts: Array.isArray(conflicts)
        ? (conflicts as ImportRowError[])
        : [],
    };
  }
  if (problem.slug === "invalid-state") {
    return {
      ...final,
      message: sentence("This check can't be imported any more.", problem),
    };
  }
  if (problem.slug === "import-failed") {
    return {
      ...final,
      message: sentence("The import failed, and nothing was saved.", problem),
      more: problem.requestId
        ? `If it fails again, quote request ID ${problem.requestId}.`
        : undefined,
    };
  }
  if (problem.status === 404) {
    return {
      ...final,
      message: NOT_FOUND,
    };
  }
  return {
    ...fallback("Couldn't import the file.", problem),
    ...final,
    retry: true,
  };
}

const NOT_FOUND = "This check was not found. Upload the file again.";

/** Why GET /imports/{id} (a `?job=` link) can't show the check. */
export function explainLoadProblem(problem: ProblemError): Explained {
  // 404 also covers someone else's check: only its creator (or USER_ADMIN) may see it.
  if (problem.status === 404) return { message: NOT_FOUND };
  return fallback("Couldn't open this check.", problem);
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
