import { screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { API_ORIGIN } from "@/lib/api/origin";
import type { components } from "@/lib/api/schema";
import type { Me } from "@/lib/permissions";
import {
  makeEmployeeDetail,
  makeHistoryRecord,
  makeMaskedDetail,
  makeMe,
  makeProblem,
  makeReference,
  makeViewer,
} from "@/test/fixtures";
import { server } from "@/test/msw/server";
import { renderInApp } from "@/test/render";
import { signedInRequest } from "@/test/server";

import EmployeePage from "./page";

type EmployeeDetail = components["schemas"]["EmployeeDetail"];
type SalaryHistory = components["schemas"]["SalaryHistory"];
type ReferenceData = components["schemas"]["ReferenceData"];
type Problem = components["schemas"]["Problem"];

const { getMe } = vi.hoisted(() => ({ getMe: vi.fn<() => Promise<Me>>() }));
vi.mock("@/lib/api/me", () => ({ getMe }));
vi.mock("next/headers", () => ({ cookies: vi.fn() }));
const { notFound } = vi.hoisted(() => ({
  notFound: vi.fn(() => {
    throw new Error("NEXT_NOT_FOUND");
  }),
}));
vi.mock("next/navigation", () => ({
  notFound,
  useRouter: () => ({ refresh: vi.fn(), push: vi.fn() }),
}));

const EMPLOYEE_URL = `${API_ORIGIN}/api/v1/employees/:id`;

const HISTORY: SalaryHistory = {
  employee_id: 2210,
  records: [
    makeHistoryRecord(),
    makeHistoryRecord({
      id: 9002,
      effective_date: "2025-04-01",
      reason: "MERIT",
      base: { amount_minor: 4_750_000, currency: "EUR" },
      base_change_pct: "5.56",
      changed_by: { id: 2, full_name: "Hema Iyer" },
      note: "Annual cycle 2025",
    }),
  ],
};

function serveEmployee(
  employee: EmployeeDetail = makeEmployeeDetail(),
  history: SalaryHistory | null = HISTORY,
) {
  server.use(
    http.get<never, never, ReferenceData>(
      `${API_ORIGIN}/api/v1/reference`,
      () => HttpResponse.json(makeReference()),
    ),
    http.get<{ id: string }, never, EmployeeDetail>(EMPLOYEE_URL, () =>
      HttpResponse.json(employee),
    ),
  );
  if (history) {
    server.use(
      http.get<{ id: string }, never, SalaryHistory>(
        `${EMPLOYEE_URL}/salary-history`,
        () => HttpResponse.json(history),
      ),
    );
  }
}

// A Server Component: call it with the route's params, then render what it returns.
async function renderPage(id: string, me: Me = makeMe(), search = "") {
  getMe.mockResolvedValue(me);
  signedInRequest();
  const page = await EmployeePage({
    params: Promise.resolve({ id }),
    searchParams: Promise.resolve({}),
  });
  renderInApp(page, { me, searchParams: search });
}

function section(name: string | RegExp) {
  return screen.getByRole("region", { name });
}

describe("/employees/[id] for an HR manager", () => {
  it("names the employee and sums up their job in one sentence", async () => {
    serveEmployee();

    await renderPage("2210");

    expect(
      screen.getByRole("heading", { level: 1, name: "Lena Müller" }),
    ).toBeVisible();
    expect(
      screen.getByText(
        "Customer Success Manager, L2, in Customer Success, Germany. Full-time since 1 Jun 2022. ACME-002210.",
      ),
    ).toBeVisible();
    expect(
      screen.getByRole("link", { name: "Back to employees" }),
    ).toHaveAttribute("href", "/employees");
  });

  it("highlights total pay and lists base pay and each component", async () => {
    serveEmployee();

    await renderPage("2210");

    const pay = section("What is Lena paid?");
    expect(within(pay).getByText("€51,820").closest("mark")).not.toBeNull();
    expect(pay).toHaveTextContent("a year in total");
    const rows = within(pay)
      .getAllByRole("definition")
      .map((dd) => dd.textContent);
    expect(rows).toEqual(["€47,500", "€600", "€3,720"]);
    expect(within(pay).getByText("Base pay")).toBeVisible();
    expect(within(pay).getByText("Transport")).toBeVisible();
    expect(within(pay).getByText("Target bonus")).toBeVisible();
  });

  it("shows a month's pay when the period is monthly (display only)", async () => {
    serveEmployee();

    await renderPage("2210", makeMe(), "?period=monthly");

    const pay = section("What is Lena paid?");
    // €51,820 ÷ 12 = €4,318.333…, half-even to the cent.
    expect(within(pay).getByText("€4,318.33")).toBeVisible();
    expect(pay).toHaveTextContent("a month in total");
  });

  it("tells how the pay got here, newest change first", async () => {
    serveEmployee();

    await renderPage("2210");

    const timeline = section("How did Lena's pay get here?");
    const items = within(timeline).getAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(items[0]).toHaveTextContent("1 Apr 2025");
    expect(items[0]).toHaveTextContent("Merit raise");
    expect(items[0]).toHaveTextContent("by Hema Iyer");
    expect(items[0]).toHaveTextContent("€45,000 to €47,500");
    expect(items[0]).toHaveTextContent("+5.6%");
    expect(items[0]).toHaveTextContent("Annual cycle 2025");
    expect(items[1]).toHaveTextContent("1 Jun 2022");
    expect(items[1]).toHaveTextContent("Hired");
    expect(items[1]).toHaveTextContent("as Customer Success Manager, L2");
  });

  it("offers every action an HR manager may take, with the main one in a phone bar", async () => {
    serveEmployee();

    await renderPage("2210");

    const [header, phoneBar] = screen.getAllByRole("button", {
      name: "Record salary change",
    });
    expect(header).toHaveClass("hidden", "sm:inline-flex");
    expect(phoneBar?.closest("[data-slot=phone-action-bar]")).toHaveClass(
      "fixed",
      "sm:hidden",
    );
    expect(screen.getByRole("button", { name: "Edit details" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Terminate" })).toBeVisible();
  });

  it("offers Reactivate, not a salary change, for a terminated employee", async () => {
    serveEmployee(
      makeEmployeeDetail({
        status: "TERMINATED",
        termination_date: "2026-02-15",
      }),
    );

    await renderPage("2210");

    expect(screen.getByText(/Terminated on 15 Feb 2026/)).toBeVisible();
    expect(screen.getByRole("button", { name: "Reactivate" })).toBeVisible();
    expect(screen.queryByRole("button", { name: "Terminate" })).toBeNull();
    expect(
      screen.queryByRole("button", { name: "Record salary change" }),
    ).toBeNull();
  });

  it("shows only the actions this person's permissions allow", async () => {
    serveEmployee();

    await renderPage(
      "2210",
      makeMe({ permissions: ["EMPLOYEE_READ", "SALARY_READ", "SALARY_WRITE"] }),
    );

    expect(
      screen.getAllByRole("button", { name: "Record salary change" }).length,
    ).toBeGreaterThan(0);
    expect(screen.queryByRole("button", { name: "Edit details" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Terminate" })).toBeNull();
  });

  it("keeps the rest of the page when the history can't load", async () => {
    serveEmployee(makeEmployeeDetail(), null);
    server.use(
      http.get<never, never, Problem>(`${EMPLOYEE_URL}/salary-history`, () =>
        HttpResponse.json(
          makeProblem("x", 503, {
            type: "about:blank",
            title: "Service Unavailable",
            request_id: "req-history",
          }),
          { status: 503 },
        ),
      ),
    );

    await renderPage("2210");

    const timeline = section("How did Lena's pay get here?");
    expect(within(timeline).getByRole("alert")).toHaveTextContent(
      "Request ID: req-history",
    );
    expect(section("What is Lena paid?")).toHaveTextContent("€51,820");
  });
});

describe("/employees/[id] for a viewer", () => {
  it("says compensation is restricted, never asks for the history, and offers no actions", async () => {
    // No salary-history handler: asking for it would fail the test.
    serveEmployee(makeMaskedDetail({ version: null }), null);

    await renderPage("2210", makeViewer());

    expect(
      within(section("What is Lena paid?")).getByText(
        "Compensation details are restricted for your role.",
      ),
    ).toBeVisible();
    expect(screen.queryByRole("region", { name: /pay get here/ })).toBeNull();
    expect(screen.queryByText(/€/)).toBeNull();
    expect(
      screen.queryByRole("button", { name: "Record salary change" }),
    ).toBeNull();
    expect(screen.queryByRole("button", { name: "Edit details" })).toBeNull();
    expect(section("Who is Lena?")).toHaveTextContent(
      "lena.mueller@acme.example",
    );
  });
});

describe("/employees/[id] that doesn't exist", () => {
  it("is a 404 when the API doesn't know the id", async () => {
    server.use(
      http.get<never, never, ReferenceData>(
        `${API_ORIGIN}/api/v1/reference`,
        () => HttpResponse.json(makeReference()),
      ),
      http.get<never, never, Problem>(EMPLOYEE_URL, () =>
        HttpResponse.json(makeProblem("not-found", 404), { status: 404 }),
      ),
      http.get<never, never, Problem>(`${EMPLOYEE_URL}/salary-history`, () =>
        HttpResponse.json(makeProblem("not-found", 404), { status: 404 }),
      ),
    );

    await expect(renderPage("999")).rejects.toThrow("NEXT_NOT_FOUND");
  });

  it.each(["abc", "0", "-3", "1.5", "99999999999999999999"])(
    "is a 404 for the id %j, without asking the API",
    async (id) => {
      await expect(renderPage(id)).rejects.toThrow("NEXT_NOT_FOUND");
    },
  );
});
