import Link from "next/link";

import { PageTitle } from "@/components/print";
import { Button, buttonVariants } from "@/components/ui/button";
import type { components } from "@/lib/api/schema";
import { formatDateTime } from "@/lib/dates";

type ImportJobReport = components["schemas"]["ImportJobReport"];

/**
 * A `?job=` link to a check that can no longer be imported: it went through already, it
 * expired (24 hours), or its commit failed and nothing was saved.
 */
export function EndedStep({
  report,
  onUploadAgain,
}: {
  report: ImportJobReport;
  onUploadAgain: () => void;
}) {
  const committed = report.status === "COMMITTED";
  return (
    <>
      <PageTitle title={TITLES[report.status]}>
        {committed
          ? report.committed_at
            ? `${report.filename} was imported on ${formatDateTime(report.committed_at)}.`
            : `${report.filename} was imported.`
          : SENTENCES[report.status]}
      </PageTitle>
      <div className="mt-8 flex flex-wrap items-center gap-x-4 gap-y-3">
        {committed ? (
          <Link
            href="/employees"
            className={buttonVariants({
              className: "no-underline hover:text-paper",
            })}
          >
            See them in the employee list
          </Link>
        ) : null}
        <Button
          variant={committed ? "secondary" : "primary"}
          onClick={onUploadAgain}
        >
          {committed ? "Import another file" : "Upload the file again"}
        </Button>
      </div>
    </>
  );
}

const TITLES: Record<ImportJobReport["status"], string> = {
  DRY_RUN: "Check your file",
  COMMITTED: "This file was imported",
  EXPIRED: "This check has expired",
  FAILED: "This import failed",
};

const SENTENCES: Record<ImportJobReport["status"], string> = {
  DRY_RUN: "",
  COMMITTED: "",
  EXPIRED:
    "A check is kept for 24 hours. Upload the file again to check it again.",
  FAILED: "Nothing was saved. Upload the file again to retry.",
};
