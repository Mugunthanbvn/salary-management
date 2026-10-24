import type { components } from "@/lib/api/schema";

type ImportRowError = components["schemas"]["ImportRowError"];

const COLUMNS = ["row", "column", "code", "message", "value"] as const;

/** Cells a spreadsheet would run as a formula (docs/11-import-export.md §6.3). */
const FORMULA_START = /^[=+\-@\t\r]/;

/** One CSV cell: formula characters neutralised with `'`, then RFC 4180 quoting. */
function cell(value: string | number | null): string {
  let text = value === null ? "" : String(value);
  if (FORMULA_START.test(text)) text = `'${text}`;
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

/**
 * The dry-run's problems as a CSV (`row, column, code, message, value`), made in the browser
 * from the JSON the API sent (docs/11-import-export.md §5.5). UTF-8 with a BOM, so Excel
 * shows accents, and CRLF line ends.
 */
export function problemsCsv(errors: ImportRowError[]): string {
  const lines = [
    COLUMNS.join(","),
    ...errors.map((error) => COLUMNS.map((key) => cell(error[key])).join(",")),
  ];
  return `﻿${lines.map((line) => `${line}\r\n`).join("")}`;
}

/** "q4-new-hires.xlsx" → "q4-new-hires-problems.csv". */
export function errorReportName(filename: string): string {
  return `${filename.replace(/\.[^.]+$/, "")}-problems.csv`;
}
