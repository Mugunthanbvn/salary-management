import { describe, expect, it } from "vitest";

import { makeRowError } from "@/test/fixtures";

import { errorReportName, problemsCsv } from "./error-report";

describe("problemsCsv", () => {
  it("lists row, column, code, message and value, one problem per line", () => {
    const csv = problemsCsv([
      makeRowError(),
      makeRowError({
        row: 31,
        column: "base_salary",
        code: "required",
        message: "base_salary is required.",
        value: null,
      }),
    ]);

    expect(csv).toBe(
      "\uFEFFrow,column,code,message,value\r\n" +
        "12,email,duplicate_in_file,Same email as row 4.,a.rao@acme.example\r\n" +
        "31,base_salary,required,base_salary is required.,\r\n",
    );
  });

  it("quotes commas and quotes, and never lets a value run as a formula", () => {
    const csv = problemsCsv([
      makeRowError({ message: 'Write "46000", not 46,000.', value: "=1+1" }),
    ]);

    expect(csv.split("\r\n")[1]).toBe(
      `12,email,duplicate_in_file,"Write ""46000"", not 46,000.",'=1+1`,
    );
  });
});

describe("errorReportName", () => {
  it.each([
    ["q4-new-hires.xlsx", "q4-new-hires-problems.csv"],
    ["hires.csv", "hires-problems.csv"],
    ["noext", "noext-problems.csv"],
  ])("names the report after %s", (filename, expected) => {
    expect(errorReportName(filename)).toBe(expected);
  });
});
