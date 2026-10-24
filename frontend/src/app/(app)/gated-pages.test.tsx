import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { API_ORIGIN } from "@/lib/api/origin";
import type { components } from "@/lib/api/schema";
import type { Me } from "@/lib/permissions";
import { makeMe, makeReference, VIEWER_PERMISSIONS } from "@/test/fixtures";
import { server } from "@/test/msw/server";
import { renderInApp } from "@/test/render";
import { signedInRequest } from "@/test/server";

import AskPage from "./ask/page";
import ImportPage from "./employees/import/page";
import NewEmployeePage from "./employees/new/page";

type ReferenceData = components["schemas"]["ReferenceData"];

const { getMe } = vi.hoisted(() => ({ getMe: vi.fn<() => Promise<Me>>() }));
vi.mock("@/lib/api/me", () => ({ getMe }));
vi.mock("next/headers", () => ({ cookies: vi.fn() }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn(), push: vi.fn() }),
}));

// The add-employee form fills its dropdowns from GET /reference.
beforeEach(() => {
  signedInRequest();
  server.use(
    http.get<never, never, ReferenceData>(
      `${API_ORIGIN}/api/v1/reference`,
      () => HttpResponse.json(makeReference()),
    ),
  );
});

// Server Components: call the page, then render what it returns.
async function renderPage(page: () => Promise<React.ReactElement>, me: Me) {
  getMe.mockResolvedValue(me);
  renderInApp(await page(), { me });
}

describe("pages that need a permission", () => {
  it.each([
    { path: "/employees/import", page: ImportPage, title: "Import employees" },
    { path: "/employees/new", page: NewEmployeePage, title: "Add an employee" },
    { path: "/ask", page: AskPage, title: "Ask about pay" },
  ])("$path opens for an HR manager", async ({ page, title }) => {
    await renderPage(page, makeMe());

    expect(
      screen.getByRole("heading", { level: 1, name: title }),
    ).toBeVisible();
  });

  it.each([
    { path: "/employees/import", page: ImportPage },
    { path: "/employees/new", page: NewEmployeePage },
  ])("$path tells a viewer they have no access", async ({ page }) => {
    await renderPage(page, makeMe({ permissions: VIEWER_PERMISSIONS }));

    expect(
      screen.getByRole("heading", { name: "You don't have access to this" }),
    ).toBeVisible();
  });

  it("/ask opens the question box for anyone with ASK", async () => {
    await renderPage(AskPage, makeMe({ permissions: VIEWER_PERMISSIONS }));

    expect(screen.getByLabelText("Ask a question about pay")).toBeVisible();
  });

  it("/ask tells someone without ASK they have no access", async () => {
    await renderPage(AskPage, makeMe({ permissions: ["INSIGHTS_READ"] }));

    expect(
      screen.getByRole("heading", { name: "You don't have access to this" }),
    ).toBeVisible();
    expect(screen.queryByLabelText("Ask a question about pay")).toBeNull();
  });

  it("/employees/new needs SALARY_WRITE too: a new hire comes with a salary", async () => {
    await renderPage(
      NewEmployeePage,
      makeMe({
        permissions: ["EMPLOYEE_READ", "EMPLOYEE_WRITE", "SALARY_READ"],
      }),
    );

    expect(
      screen.getByRole("heading", { name: "You don't have access to this" }),
    ).toBeVisible();
  });

  it("/employees/new shows the form to an HR manager", async () => {
    await renderPage(NewEmployeePage, makeMe());

    expect(screen.getByRole("form", { name: "New employee" })).toBeVisible();
  });

  it("/ask says Ask is turned off when the API has it off", async () => {
    await renderPage(AskPage, makeMe({ features: { ask: false } }));

    expect(
      screen.getByRole("heading", { name: "You don't have access to this" }),
    ).toBeVisible();
    expect(
      screen.getByText("Ask is turned off on this deployment."),
    ).toBeVisible();
  });
});
