import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { Toaster } from "@/components/ui/sonner";
import type { components } from "@/lib/api/schema";
import {
  makeImportReport,
  makeProblem,
  makeRowError,
  makeValidationProblem,
} from "@/test/fixtures";
import { server } from "@/test/msw/server";
import { renderInApp } from "@/test/render";
import { makeFile, useNodeFormData } from "@/test/upload";

import { ImportFlow } from "./import-flow";

type ImportCommitResult = components["schemas"]["ImportCommitResult"];
type ImportJobReport = components["schemas"]["ImportJobReport"];
type Problem = components["schemas"]["Problem"];
type ValidationProblem = components["schemas"]["ValidationProblem"];

const UPLOAD_URL = "/api/v1/imports";
const COMMIT_URL = "/api/v1/imports/:id/commit";
const JOB_URL = "/api/v1/imports/:id";

function renderFlow(searchParams = "") {
  const urls: URLSearchParams[] = [];
  renderInApp(
    <>
      <ImportFlow />
      <Toaster />
    </>,
    {
      searchParams,
      onUrlUpdate: ({ searchParams: next }) => urls.push(next),
    },
  );
  return urls;
}

beforeEach(async () => {
  await useNodeFormData();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function csvFile(name = "q4-new-hires.csv") {
  return makeFile(name, "employee_code,first_name\n", "text/csv");
}

async function upload(file = csvFile()) {
  await userEvent.upload(screen.getByLabelText(/Choose a file/), file);
}

/** POST /imports answers with this report; returns the file names it received. */
function serveUpload(report: ImportJobReport = makeImportReport()) {
  const received: string[] = [];
  server.use(
    http.post<never, never, ImportJobReport>(
      UPLOAD_URL,
      async ({ request }) => {
        const file = (await request.formData()).get("file");
        if (file && typeof file === "object") received.push(file.name);
        return HttpResponse.json(report, { status: 201 });
      },
    ),
  );
  return received;
}

const WITH_ERRORS = makeImportReport({
  row_count: 248,
  valid_count: 245,
  error_count: 4,
  errors: [
    makeRowError(),
    makeRowError({
      row: 31,
      column: "job_role",
      code: "unknown_value",
      message:
        "'Sr Engineer' is not a known job role. Did you mean 'Software Engineer'?",
      value: "Sr Engineer",
    }),
    makeRowError({
      row: 31,
      column: "base_salary",
      code: "required",
      message: "base_salary is required.",
      value: null,
    }),
    makeRowError({
      row: 77,
      column: "base_salary",
      code: "too_many_decimals",
      message: "JPY amounts can't have decimals.",
      value: "450000.5",
    }),
  ],
});

describe("ImportFlow: upload", () => {
  it("offers the CSV and Excel templates", () => {
    renderFlow();

    expect(screen.getByRole("link", { name: /CSV template/ })).toHaveAttribute(
      "href",
      "/api/v1/imports/template?format=csv",
    );
    expect(
      screen.getByRole("link", { name: /Excel template/ }),
    ).toHaveAttribute("href", "/api/v1/imports/template?format=xlsx");
  });

  it("checks the chosen file and shows what will be imported", async () => {
    const received = serveUpload();
    const urls = renderFlow();

    await upload();

    expect(
      await screen.findByRole("heading", {
        level: 1,
        name: "Ready to import 3 employees",
      }),
    ).toBeVisible();
    expect(received).toEqual(["q4-new-hires.csv"]);
    expect(urls.at(-1)?.get("job")).toBe("31");
    expect(screen.getByText(/q4-new-hires\.csv has 3 rows\./)).toBeVisible();
    const preview = screen.getByRole("table", { name: /Who will be added/ });
    const ananya = within(preview).getByRole("row", { name: /Ananya Rao/ });
    expect(ananya).toHaveTextContent("ACME-010001");
    expect(ananya).toHaveTextContent("₹15,00,000");
    expect(ananya).toHaveTextContent("₹16,20,000");
    expect(
      within(preview).getByRole("row", { name: /Taro Yamada/ }),
    ).toHaveTextContent("¥4,500,000");
    expect(screen.getByText(/kept until 25 Oct 2026, 10:45 UTC/)).toBeVisible();
    expect(
      screen.getByRole("button", { name: "Import 3 employees" }),
    ).toBeEnabled();
  });

  it("lists the problems grouped by row, and won't import until they are fixed", async () => {
    serveUpload(WITH_ERRORS);
    renderFlow();

    await upload();

    expect(
      await screen.findByRole("heading", {
        level: 1,
        name: "3 rows need fixing",
      }),
    ).toBeVisible();
    expect(screen.getByText(/245 are ready to import/)).toBeVisible();
    const table = screen.getByRole("table", { name: /Problems by row/ });
    const row31 = within(table).getByRole("rowgroup", { name: "Row 31" });
    expect(within(row31).getAllByRole("row")).toHaveLength(2);
    expect(row31).toHaveTextContent("job_role");
    expect(row31).toHaveTextContent("Did you mean 'Software Engineer'?");
    expect(row31).toHaveTextContent("(empty)");
    const cards = screen.getByRole("list", { name: /Problems by row/ });
    expect(within(cards).getAllByRole("listitem")).toHaveLength(3);
    expect(
      screen.getByRole("button", { name: "Import 245 employees" }),
    ).toBeDisabled();
  });

  it.each([
    {
      why: "the header row doesn't match the template",
      status: 400,
      body: makeProblem("bad-request", 400, {
        title: "Bad request",
        detail: "Unknown column 'emial'.",
        expected_headers: ["employee_code", "first_name", "email"],
      }),
      says: [
        "The columns don't match the template. Unknown column 'emial'.",
        "Expected columns: employee_code, first_name, email",
      ],
    },
    {
      why: "the file can't be read",
      status: 400,
      body: makeProblem("bad-request", 400, {
        title: "Bad request",
        detail: "File is not UTF-8.",
      }),
      says: ["This file can't be read. File is not UTF-8."],
    },
    {
      why: "the file is too large",
      status: 413,
      body: makeProblem("payload-too-large", 413, { title: "Too large" }),
      says: [
        "This file is larger than 4 MB. Split it into smaller files and upload each one.",
      ],
    },
    {
      why: "the file is not CSV or XLSX",
      status: 415,
      body: makeProblem("unsupported-media-type", 415, { title: "Bad type" }),
      says: [
        "Only .csv and .xlsx files can be imported. In Excel, save the file as CSV UTF-8 or as an Excel workbook (.xlsx).",
      ],
    },
    {
      why: "the file has too many rows",
      status: 422,
      body: makeValidationProblem([
        {
          loc: ["body", "file"],
          code: "too_many_rows",
          message: "The file has 10,001 rows; the limit is 10,000.",
        },
      ]),
      says: [
        "This file has more than 10,000 rows. Split it into smaller files and upload each one.",
      ],
    },
  ])("says so in plain words when $why", async ({ status, body, says }) => {
    server.use(
      http.post<never, never, Problem | ValidationProblem>(UPLOAD_URL, () =>
        HttpResponse.json(body, { status }),
      ),
    );
    renderFlow();

    await upload();

    const alert = await screen.findByRole("alert");
    for (const text of says) expect(alert).toHaveTextContent(text);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      "Import employees",
    );
  });
});

describe("ImportFlow: import", () => {
  async function checkedFile() {
    serveUpload();
    renderFlow();
    await upload();
    await screen.findByRole("heading", {
      level: 1,
      name: "Ready to import 3 employees",
    });
  }

  function serveCommit(status: number, body: ImportCommitResult | Problem) {
    const committed: string[] = [];
    server.use(
      http.post<{ id: string }, never, ImportCommitResult | Problem>(
        COMMIT_URL,
        ({ params }) => {
          committed.push(params.id);
          return HttpResponse.json(body, { status });
        },
      ),
    );
    return committed;
  }

  it("imports the checked file and says how many were added", async () => {
    const committed = serveCommit(200, {
      id: 31,
      status: "COMMITTED",
      inserted: 3,
    });
    await checkedFile();

    await userEvent.click(
      screen.getByRole("button", { name: "Import 3 employees" }),
    );

    expect(await screen.findByText("Imported 3 employees")).toBeVisible();
    expect(committed).toEqual(["31"]);
    expect(
      screen.getByRole("heading", { level: 1, name: "3 employees imported" }),
    ).toBeVisible();
    expect(
      screen.getByRole("link", { name: "See them in the employee list" }),
    ).toHaveAttribute("href", "/employees");
  });

  it.each([
    {
      why: "the check expired",
      status: 409,
      body: makeProblem("invalid-state", 409, {
        title: "Invalid state",
        detail:
          "This dry-run expired 24 hours after the upload. Upload the file again.",
      }),
      says: [
        "This check can't be imported any more. This dry-run expired 24 hours after the upload. Upload the file again.",
      ],
    },
    {
      why: "the import failed",
      status: 500,
      body: makeProblem("import-failed", 500, {
        title: "Import failed",
        detail:
          "Import 31 failed and nothing was written. Upload the file again to retry.",
        request_id: "req-500",
        job_id: 31,
      }),
      says: [
        "The import failed, and nothing was saved. Import 31 failed and nothing was written.",
        "req-500",
      ],
    },
  ])(
    "says so, and imports nothing, when $why",
    async ({ status, body, says }) => {
      serveCommit(status, body);
      await checkedFile();

      await userEvent.click(
        screen.getByRole("button", { name: "Import 3 employees" }),
      );

      const alert = await screen.findByRole("alert");
      for (const text of says) expect(alert).toHaveTextContent(text);
      expect(
        screen.getByRole("button", { name: "Import 3 employees" }),
      ).toBeDisabled();
      expect(
        screen.getByRole("button", { name: "Upload the file again" }),
      ).toBeVisible();
    },
  );

  it("shows which rows someone added since the check", async () => {
    serveCommit(
      409,
      makeProblem("duplicate", 409, {
        title: "Duplicate",
        detail: "2 rows are now already in the directory (see conflicts).",
        conflicts: [
          makeRowError({
            row: 3,
            column: "email",
            code: "duplicate_in_db",
            message: "An employee with this email already exists.",
            value: "lena.weber@acme.example",
          }),
          makeRowError({
            row: 4,
            column: "employee_code",
            code: "duplicate_in_db",
            message: "An employee with this code already exists.",
            value: "ACME-010003",
          }),
        ],
      }),
    );
    await checkedFile();

    await userEvent.click(
      screen.getByRole("button", { name: "Import 3 employees" }),
    );

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(
      "Nothing was imported: some of these people were added after the check.",
    );
    const table = within(alert).getByRole("table", {
      name: /Already in the directory/,
    });
    expect(
      within(table).getByRole("rowgroup", { name: "Row 3" }),
    ).toHaveTextContent("lena.weber@acme.example");
    expect(
      within(table).getByRole("rowgroup", { name: "Row 4" }),
    ).toHaveTextContent("ACME-010003");
  });
});

describe("ImportFlow: a check in the URL", () => {
  function serveJob(status: number, body: ImportJobReport | Problem) {
    const asked: string[] = [];
    server.use(
      http.get<{ id: string }, never, ImportJobReport | Problem>(
        JOB_URL,
        ({ params }) => {
          asked.push(params.id);
          return HttpResponse.json(body, { status });
        },
      ),
    );
    return asked;
  }

  it("reopens the dry-run after a refresh", async () => {
    const asked = serveJob(200, WITH_ERRORS);
    renderFlow("?job=31");

    expect(
      await screen.findByRole("heading", {
        level: 1,
        name: "3 rows need fixing",
      }),
    ).toBeVisible();
    expect(asked).toEqual(["31"]);
    expect(
      screen.getByRole("button", { name: "Import 245 employees" }),
    ).toBeDisabled();
  });

  it.each([
    {
      status: "COMMITTED" as const,
      title: "This file was imported",
      says: "q4-new-hires.csv was imported on 24 Oct 2026, 11:02 UTC.",
    },
    {
      status: "EXPIRED" as const,
      title: "This check has expired",
      says: "A check is kept for 24 hours. Upload the file again to check it again.",
    },
    {
      status: "FAILED" as const,
      title: "This import failed",
      says: "Nothing was saved. Upload the file again to retry.",
    },
  ])(
    "says when the check is $status and can't be imported",
    async ({ status, title, says }) => {
      serveJob(
        200,
        makeImportReport({
          status,
          preview: [],
          committed_at: status === "COMMITTED" ? "2026-10-24T11:02:00Z" : null,
        }),
      );
      renderFlow("?job=31");

      expect(
        await screen.findByRole("heading", { level: 1, name: title }),
      ).toBeVisible();
      expect(screen.getByText(says)).toBeVisible();
      expect(screen.queryByRole("button", { name: /^Import \d/ })).toBeNull();
    },
  );

  it("offers a new upload when the check is not found", async () => {
    serveJob(
      404,
      makeProblem("not-found", 404, {
        title: "Not found",
        detail: "Import 31 was not found.",
      }),
    );
    const urls = renderFlow("?job=31");

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "This check was not found. Upload the file again.",
    );
    expect(
      screen.getByRole("heading", { level: 1, name: "Import employees" }),
    ).toBeVisible();
    expect(urls.at(-1)?.has("job")).toBe(false);
  });
});
