import { screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { API_ORIGIN } from "@/lib/api/origin";
import type { components } from "@/lib/api/schema";
import type { Me } from "@/lib/permissions";
import {
  makeEmployeePage,
  makeMaskedListItem,
  makeMe,
  makeProblem,
  makeReference,
  makeViewer,
} from "@/test/fixtures";
import { server } from "@/test/msw/server";
import { renderInApp } from "@/test/render";
import { signedInRequest } from "@/test/server";

import EmployeesPage from "./page";

type EmployeePage = components["schemas"]["EmployeePage"];
type ReferenceData = components["schemas"]["ReferenceData"];
type Problem = components["schemas"]["Problem"];

const { getMe } = vi.hoisted(() => ({ getMe: vi.fn<() => Promise<Me>>() }));
vi.mock("@/lib/api/me", () => ({ getMe }));
vi.mock("next/headers", () => ({ cookies: vi.fn() }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn(), push: vi.fn() }),
}));

type Search = Record<string, string | string[]>;

/** Serves GET /reference and GET /employees; returns the query the list was asked with. */
function serveDirectory(page: EmployeePage = makeEmployeePage()) {
  const seen: { query: URLSearchParams | null } = { query: null };
  server.use(
    http.get<never, never, ReferenceData>(
      `${API_ORIGIN}/api/v1/reference`,
      () => HttpResponse.json(makeReference()),
    ),
    http.get<never, never, EmployeePage>(
      `${API_ORIGIN}/api/v1/employees`,
      ({ request }) => {
        seen.query = new URL(request.url).searchParams;
        return HttpResponse.json(page);
      },
    ),
  );
  return seen;
}

// A Server Component: call it with the page's search params, then render what it returns.
async function renderPage(search: Search, me: Me = makeMe()) {
  getMe.mockResolvedValue(me);
  signedInRequest();
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(search)) {
    for (const item of [value].flat()) query.append(key, item);
  }
  const page = await EmployeesPage({
    params: Promise.resolve({}),
    searchParams: Promise.resolve(search),
  });
  renderInApp(page, { me, searchParams: `?${query.toString()}` });
}

describe("/employees", () => {
  it("asks the API for the URL's filters, sort and page", async () => {
    const seen = serveDirectory();

    await renderPage({
      q: "müller",
      country: ["DE", "FR"],
      level: "L3",
      sort: "-hire_date",
      page: "2",
    });

    expect(seen.query?.get("q")).toBe("müller");
    expect(seen.query?.getAll("country")).toEqual(["DE", "FR"]);
    expect(seen.query?.get("level")).toBe("L3");
    expect(seen.query?.get("sort")).toBe("-hire_date");
    expect(seen.query?.get("page")).toBe("2");
    expect(seen.query?.has("period")).toBe(false);
  });

  it("leads with the question and says how many active employees there are", async () => {
    serveDirectory(makeEmployeePage(undefined, { total: 9412 }));

    await renderPage({});

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: "Who are you looking for?",
      }),
    ).toBeVisible();
    expect(screen.getByText("9,412 active employees.")).toBeVisible();
  });

  it("says how many match once the list is filtered", async () => {
    serveDirectory(makeEmployeePage(undefined, { total: 37 }));

    await renderPage({ country: "DE" });

    expect(screen.getByText("37 employees match.")).toBeVisible();
  });

  it("offers Add employee and Import to an HR manager", async () => {
    serveDirectory();

    await renderPage({});

    expect(screen.getByRole("link", { name: "Add employee" })).toHaveAttribute(
      "href",
      "/employees/new",
    );
    expect(
      screen.getByRole("link", { name: "Import from Excel" }),
    ).toHaveAttribute("href", "/employees/import");
  });

  it("never asks the API for a viewer's salary filters, and shows them no pay", async () => {
    const seen = serveDirectory(makeEmployeePage([makeMaskedListItem()]));

    await renderPage(
      { country: "DE", salary_min: "4000000", sort: "-current_base" },
      makeViewer(),
    );

    expect(seen.query?.has("salary_min")).toBe(false);
    expect(seen.query?.has("sort")).toBe(false);
    const table = screen.getByRole("table", { name: /Employees/ });
    expect(
      within(table).queryByRole("columnheader", { name: /pay/i }),
    ).toBeNull();
    expect(screen.queryByRole("link", { name: "Add employee" })).toBeNull();
    expect(
      screen.queryByRole("link", { name: "Import from Excel" }),
    ).toBeNull();
  });

  it.each([
    { who: "an HR manager", me: makeMe(), label: "Export" },
    { who: "a viewer", me: makeViewer(), label: "Export (no salary data)" },
  ])("offers $who an export of the list", async ({ me, label }) => {
    serveDirectory();

    await renderPage({}, me);

    expect(screen.getByRole("button", { name: label })).toBeVisible();
  });

  it("offers no export without the EXPORT permission", async () => {
    serveDirectory();

    await renderPage(
      {},
      makeMe({ permissions: ["EMPLOYEE_READ", "INSIGHTS_READ"] }),
    );

    expect(screen.queryByRole("button", { name: /^Export/ })).toBeNull();
  });

  it("shows the API's problem, with its request id, when the list fails", async () => {
    server.use(
      http.get<never, never, ReferenceData>(
        `${API_ORIGIN}/api/v1/reference`,
        () => HttpResponse.json(makeReference()),
      ),
      http.get<never, never, Problem>(`${API_ORIGIN}/api/v1/employees`, () =>
        HttpResponse.json(
          makeProblem("validation", 422, {
            title: "Validation failed",
            detail: "1 field is invalid.",
            request_id: "req-list",
          }),
          { status: 422 },
        ),
      ),
    );

    await renderPage({});

    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("Validation failed");
    expect(alert).toHaveTextContent("Request ID: req-list");
  });
});
