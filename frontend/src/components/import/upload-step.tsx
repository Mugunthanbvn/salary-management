"use client";

import { cn } from "cn";
import { useState, type ChangeEvent, type DragEvent } from "react";

import { MarginNote, PageTitle, Section } from "@/components/print";

import { ImportSteps } from "./import-steps";
import type { Explained } from "./messages";
import { ProblemNote } from "./problem-note";

const ERROR_ID = "upload-error";

/**
 * Step 1: the templates, the rules a file must follow, and the file picker. Dropping a file
 * works on a desktop too; a phone uses the picker. Choosing a file checks it straight away.
 */
export function UploadStep({
  uploading,
  error,
  onFile,
}: {
  /** The name of the file being checked, while it is. */
  uploading: string | null;
  error: Explained | null;
  onFile: (file: File) => void;
}) {
  const [dragging, setDragging] = useState(false);

  function onChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    // Cleared, so choosing the same file again (once fixed) checks it again.
    event.target.value = "";
    if (file) onFile(file);
  }

  function onDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setDragging(false);
    const file = event.dataTransfer.files[0];
    if (file && !uploading) onFile(file);
  }

  return (
    <>
      <ImportSteps current="Upload" />
      <PageTitle title="Import employees">
        Upload a CSV or Excel file of new hires, check it, then add them all at
        once.
      </PageTitle>
      <Section question="What should the file look like?">
        <p className="max-w-[640px] text-[17px] leading-normal">
          One row per new hire, with the columns of the template. Amounts are
          yearly, in the currency of the person&apos;s country, written as plain
          numbers (52000.00).
        </p>
        <ul className="mt-3 flex flex-wrap gap-x-6">
          <li>
            <a
              href="/api/v1/imports/template?format=csv"
              download
              className="inline-flex min-h-11 items-center text-[15px]"
            >
              Download the CSV template
            </a>
          </li>
          <li>
            <a
              href="/api/v1/imports/template?format=xlsx"
              download
              className="inline-flex min-h-11 items-center text-[15px]"
            >
              Download the Excel template
            </a>
          </li>
        </ul>
        <MarginNote className="mt-3 max-w-[640px]">
          Saving from Excel? Keep it as .xlsx, or choose &ldquo;CSV UTF-8 (Comma
          delimited)&rdquo;. A file can be up to 4 MB and 10,000 rows.
        </MarginNote>
      </Section>
      <Section question="Which file do you want to check?">
        <label
          onDragOver={(event) => {
            event.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          className={cn(
            "flex min-h-32 cursor-pointer flex-col items-center justify-center gap-1 rounded-control border-2 border-dashed border-ink px-4 py-6 text-center focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-blue-pen",
            dragging && "bg-highlighter",
            uploading && "cursor-wait opacity-60",
          )}
        >
          <span className="text-[17px] font-bold underline underline-offset-4">
            Choose a file (.csv or .xlsx)
          </span>
          <span className="hidden text-[15px] text-ink-2 sm:block">
            or drop it here
          </span>
          <input
            type="file"
            accept=".csv,.xlsx"
            disabled={uploading !== null}
            aria-describedby={error ? ERROR_ID : undefined}
            onChange={onChange}
            className="sr-only"
          />
        </label>
        <p aria-live="polite" className="mt-3 text-[15px] text-ink-2">
          {uploading
            ? `Checking ${uploading}…`
            : "Nothing is saved yet: you will see every row first."}
        </p>
        {error ? <ProblemNote id={ERROR_ID} problem={error} /> : null}
      </Section>
    </>
  );
}
