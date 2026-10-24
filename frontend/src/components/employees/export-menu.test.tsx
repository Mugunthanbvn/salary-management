import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { Toaster } from "@/components/ui/sonner";
import type { components } from "@/lib/api/schema";
import {
  makeMe,
  makeProblem,
  makeReference,
  makeViewer,
} from "@/test/fixtures";
import { server } from "@/test/msw/server";
import { renderInApp } from "@/test/render";

import { ExportMenu } from "./export-menu";

type Problem = components["schemas"]["Problem"];

const { saveFile } = vi.hoisted(() => ({ saveFile: vi.fn() }));
vi.mock("@/lib/download", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/download")>()),
  saveFile,
}));

const EXPORT_URL = "/api/v1/employees/export";

function renderMenu(searchParams = "", me = makeMe()) {
  renderInApp(
    <>
      <ExportMenu reference={makeReference()} />
      <Toaster />
    </>,
    { me, searchParams },
  );
}

async function exportAs(label: RegExp, format: string) {
  await userEvent.click(screen.getByRole("button", { name: label }));
  await userEvent.click(screen.getByRole("menuitem", { name: format }));
}

describe("ExportMenu", () => {
  it("downloads exactly the directory's filters and sort, without paging", async () => {
    let asked: URL | undefined;
    server.use(
      http.get<never, never, string>(EXPORT_URL, ({ request }) => {
        asked = new URL(request.url);
        return new HttpResponse("employee_code\n", {
          headers: {
            "Content-Type": "text/csv; charset=utf-8",
            "Content-Disposition":
              'attachment; filename="acme-employees-2026-10-24.csv"',
          },
        });
      }),
    );
    renderMenu(
      "?country=DE&level=L3&sort=-current_base&page=3&page_size=50&period=monthly",
    );

    await exportAs(/^Export$/, "CSV");

    await waitFor(() => expect(saveFile).toHaveBeenCalledTimes(1));
    const [file, filename] = saveFile.mock.calls[0] as [Blob, string];
    expect(filename).toBe("acme-employees-2026-10-24.csv");
    expect(await file.text()).toBe("employee_code\n");
    expect(Object.fromEntries(asked!.searchParams)).toEqual({
      country: "DE",
      level: "L3",
      status: "ACTIVE",
      sort: "-current_base",
      format: "csv",
    });
  });

  it("asks for an Excel file when Excel is chosen", async () => {
    let format: string | null = null;
    server.use(
      http.get<never, never, string>(EXPORT_URL, ({ request }) => {
        format = new URL(request.url).searchParams.get("format");
        return new HttpResponse("xlsx");
      }),
    );
    renderMenu();

    await exportAs(/^Export$/, "Excel (.xlsx)");

    await waitFor(() =>
      expect(saveFile).toHaveBeenCalledWith(
        expect.anything(),
        "acme-employees.xlsx",
      ),
    );
    expect(format).toBe("xlsx");
  });

  it("tells a viewer the export has no salary data", () => {
    renderMenu("", makeViewer());

    expect(
      screen.getByRole("button", { name: "Export (no salary data)" }),
    ).toBeVisible();
  });

  it("says why when the API refuses the export", async () => {
    server.use(
      http.get<never, never, Problem>(EXPORT_URL, () =>
        HttpResponse.json(
          makeProblem("forbidden", 403, {
            title: "Forbidden",
            detail: "Filtering by salary needs SALARY_READ.",
          }),
          { status: 403 },
        ),
      ),
    );
    renderMenu();

    await exportAs(/^Export$/, "CSV");

    expect(
      await screen.findByText(
        "Couldn't export: Filtering by salary needs SALARY_READ.",
      ),
    ).toBeVisible();
    expect(saveFile).not.toHaveBeenCalled();
  });
});
