"use client";

import { Highlight, MarginNote, PageTitle, Section } from "@/components/print";
import { Button } from "@/components/ui/button";
import type { components } from "@/lib/api/schema";
import { formatDateTime } from "@/lib/dates";
import { saveFile } from "@/lib/download";
import { formatCount } from "@/lib/numbers";

import { errorReportName, problemsCsv } from "./error-report";
import { ImportSteps } from "./import-steps";
import type { CommitProblem } from "./messages";
import { PreviewRows } from "./preview-rows";
import { ProblemNote } from "./problem-note";
import { RowErrors } from "./row-errors";

type ImportJobReport = components["schemas"]["ImportJobReport"];

function rows(count: number): string {
  return `${formatCount(count)} ${count === 1 ? "row" : "rows"}`;
}

function employees(count: number): string {
  return `${formatCount(count)} ${count === 1 ? "employee" : "employees"}`;
}

/**
 * Step 2: the dry-run. Problems first, grouped by spreadsheet row, then the valid rows as
 * they will be imported. Import stays disabled while any row has a problem: the API imports
 * all rows or none.
 */
export function ReviewStep({
  report,
  committing,
  commitProblem,
  onCommit,
  onUploadAgain,
}: {
  report: ImportJobReport;
  committing: boolean;
  commitProblem: CommitProblem | null;
  onCommit: () => void;
  onUploadAgain: () => void;
}) {
  const badRows = report.row_count - report.valid_count;
  const hasErrors = report.error_count > 0;
  const title = hasErrors
    ? `${rows(badRows)} ${badRows === 1 ? "needs" : "need"} fixing`
    : `Ready to import ${employees(report.valid_count)}`;
  const canCommit =
    !hasErrors &&
    report.status === "DRY_RUN" &&
    !committing &&
    (commitProblem?.retry ?? true);

  return (
    <>
      <ImportSteps current="Check" />
      <PageTitle title={title}>
        {report.filename} has {rows(report.row_count)}.{" "}
        {hasErrors ? (
          <>
            <Highlight>
              {formatCount(report.valid_count)} are ready to import.
            </Highlight>{" "}
            Nothing is saved until every row is fixed, so a bad file never
            half-imports.
          </>
        ) : (
          <>
            <Highlight>All of them are ready to import.</Highlight> They are
            added together, or not at all.
          </>
        )}
      </PageTitle>

      {hasErrors ? (
        <Section question="What needs fixing?">
          <MarginNote className="mb-4">
            Row numbers match your spreadsheet. Fix these cells in the file,
            then upload it again.
          </MarginNote>
          <RowErrors errors={report.errors} />
          <Button
            variant="link"
            className="mt-2"
            onClick={() =>
              saveFile(
                new Blob([problemsCsv(report.errors)], {
                  type: "text/csv;charset=utf-8",
                }),
                errorReportName(report.filename),
              )
            }
          >
            Download the list of problems
          </Button>
        </Section>
      ) : null}

      {report.preview.length > 0 ? (
        <Section question="Who will be added?">
          {report.preview.length < report.valid_count ? (
            <MarginNote className="mb-4">
              The first {formatCount(report.preview.length)} of the{" "}
              {rows(report.valid_count)} that are ready.
            </MarginNote>
          ) : null}
          <PreviewRows rows={report.preview} />
        </Section>
      ) : null}

      {commitProblem ? (
        <div className="mb-6">
          <ProblemNote problem={commitProblem}>
            {commitProblem.conflicts.length > 0 ? (
              <div className="mt-4">
                <RowErrors
                  errors={commitProblem.conflicts}
                  label="Already in the directory"
                />
              </div>
            ) : null}
          </ProblemNote>
        </div>
      ) : null}

      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-3 border-t-2 border-ink pt-6">
        <Button disabled={!canCommit} onClick={onCommit}>
          {committing
            ? "Importing…"
            : `Import ${employees(report.valid_count)}`}
        </Button>
        <Button variant="secondary" onClick={onUploadAgain}>
          {commitProblem && !commitProblem.retry
            ? "Upload the file again"
            : hasErrors
              ? "Upload the fixed file"
              : "Upload a different file"}
        </Button>
        <p className="text-[14px] text-ink-2">
          {hasErrors
            ? `Fix the ${rows(badRows)} in your spreadsheet and upload it again. `
            : null}
          This check is kept until {formatDateTime(report.expires_at)}.
        </p>
      </div>
    </>
  );
}
