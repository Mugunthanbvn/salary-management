import Link from "next/link";

import { PageTitle } from "@/components/print";
import { Button, buttonVariants } from "@/components/ui/button";
import { formatCount } from "@/lib/numbers";

/** Step 3: the import went through, every row at once. */
export function DoneStep({
  inserted,
  filename,
  onImportAnother,
}: {
  inserted: number;
  filename: string;
  onImportAnother: () => void;
}) {
  const people = `${formatCount(inserted)} ${inserted === 1 ? "employee" : "employees"}`;
  return (
    <>
      <PageTitle title={`${people} imported`}>
        Every row of {filename} was added, each with a starting salary record
        dated as in the file.
      </PageTitle>
      <div className="mt-8 flex flex-wrap items-center gap-x-4 gap-y-3">
        <Link
          href="/employees"
          className={buttonVariants({
            className: "no-underline hover:text-paper",
          })}
        >
          See them in the employee list
        </Link>
        <Button variant="secondary" onClick={onImportAnother}>
          Import another file
        </Button>
      </div>
    </>
  );
}
