import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ProblemError } from "@/lib/api/problem";
import type { Me } from "@/lib/permissions";
import { makeMe, VIEWER_PERMISSIONS } from "@/test/fixtures";

import { AppShell } from "./app-shell";

const { getMe } = vi.hoisted(() => ({ getMe: vi.fn<() => Promise<Me>>() }));
vi.mock("@/lib/api/me", () => ({ getMe }));
vi.mock("next/navigation", () => ({
  usePathname: () => "/employees",
  useRouter: () => ({ refresh: vi.fn() }),
}));

// AppShell is an async Server Component: call it, then render what it returns.
async function renderShell(me: Me) {
  getMe.mockResolvedValue(me);
  render(await AppShell({ children: <h1>Employees page</h1> }));
}

describe("AppShell", () => {
  it("shows the page in the main region under the signed-in person's navigation", async () => {
    await renderShell(makeMe());

    expect(
      within(screen.getByRole("main")).getByRole("heading", {
        name: "Employees page",
      }),
    ).toBeVisible();
    expect(screen.getByRole("button", { name: /Hema Iyer/ })).toBeVisible();
    expect(
      screen.getByRole("link", { name: "Skip to content" }),
    ).toHaveAttribute("href", "#main");
  });

  it.each([
    { who: "an HR manager with Ask on", me: makeMe(), ask: true },
    {
      who: "a viewer with Ask off",
      me: makeMe({ permissions: VIEWER_PERMISSIONS, features: { ask: false } }),
      ask: false,
    },
  ])(
    "builds the navigation from GET /auth/me for $who",
    async ({ me, ask }) => {
      await renderShell(me);

      for (const nav of screen.getAllByRole("navigation", { name: "Main" })) {
        expect(
          within(nav).getByRole("link", { name: "Employees" }),
        ).toHaveAttribute("aria-current", "page");
        expect(within(nav).queryByRole("link", { name: "Ask" }) !== null).toBe(
          ask,
        );
      }
    },
  );

  // A thrown server error reaches the browser as a generic message in production, so the
  // shell shows the API's problem itself.
  it("shows the API's problem, with its request id, when GET /auth/me fails", async () => {
    getMe.mockRejectedValue(
      new ProblemError({
        type: "about:blank",
        title: "Service Unavailable",
        status: 503,
        detail: "The database is not reachable.",
        instance: "/api/v1/auth/me",
        request_id: "req-503",
      }),
    );

    render(await AppShell({ children: <h1>Employees page</h1> }));

    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("Service Unavailable");
    expect(alert).toHaveTextContent("The database is not reachable.");
    expect(alert).toHaveTextContent("Request ID: req-503");
    expect(screen.getByRole("button", { name: "Try again" })).toBeVisible();
    expect(screen.queryByText("Employees page")).toBeNull();
  });
});
