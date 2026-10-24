import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { Me } from "@/lib/permissions";
import { makeMe, VIEWER_PERMISSIONS } from "@/test/fixtures";

import AskPage from "./ask/page";
import ImportPage from "./employees/import/page";
import NewEmployeePage from "./employees/new/page";

const { getMe } = vi.hoisted(() => ({ getMe: vi.fn<() => Promise<Me>>() }));
vi.mock("@/lib/api/me", () => ({ getMe }));

// Server Components: call the page, then render what it returns.
async function renderPage(page: () => Promise<React.ReactElement>, me: Me) {
  getMe.mockResolvedValue(me);
  render(await page());
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
