import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { Toaster } from "@/components/ui/sonner";
import type { components } from "@/lib/api/schema";
import type { Me } from "@/lib/permissions";
import { makeMe, VIEWER_PERMISSIONS } from "@/test/fixtures";
import { server } from "@/test/msw/server";

import { AccountMenu } from "./account-menu";
import { MeProvider } from "./me-context";

type Problem = components["schemas"]["Problem"];

const { hardNavigate } = vi.hoisted(() => ({ hardNavigate: vi.fn() }));
vi.mock("@/lib/hard-navigate", () => ({ hardNavigate }));

async function openMenu(me: Me) {
  render(
    <MeProvider me={me}>
      <AccountMenu />
    </MeProvider>,
  );
  await userEvent.click(screen.getByRole("button", { name: /Hema Iyer/ }));
  return screen.getByRole("menu");
}

describe("AccountMenu", () => {
  it("shows who is signed in, with Import and Sign out for an HR manager", async () => {
    const menu = await openMenu(makeMe());

    expect(menu).toHaveTextContent("Hema Iyer");
    expect(menu).toHaveTextContent("HR Manager");
    expect(
      screen.getByRole("menuitem", { name: "Import employees" }),
    ).toHaveAttribute("href", "/employees/import");
    expect(screen.getByRole("menuitem", { name: "Sign out" })).toBeVisible();
  });

  it("leaves out Import for someone without the IMPORT permission", async () => {
    await openMenu(makeMe({ permissions: VIEWER_PERMISSIONS }));

    expect(
      screen.queryByRole("menuitem", { name: "Import employees" }),
    ).toBeNull();
    expect(screen.getByRole("menuitem", { name: "Sign out" })).toBeVisible();
  });

  it("signs out through the API, then opens the login page", async () => {
    let signedOut = false;
    server.use(
      // 204 No Content: the API clears the session cookie.
      http.post<never, never, null>("/api/v1/auth/logout", () => {
        signedOut = true;
        return new HttpResponse(null, { status: 204 });
      }),
    );
    await openMenu(makeMe());

    await userEvent.click(screen.getByRole("menuitem", { name: "Sign out" }));

    await waitFor(() => expect(hardNavigate).toHaveBeenCalledWith("/login"));
    expect(signedOut).toBe(true);
  });

  it("stays on the page and says so when signing out fails", async () => {
    server.use(
      http.post<never, never, Problem>("/api/v1/auth/logout", () =>
        HttpResponse.json(
          {
            type: "about:blank",
            title: "Internal Server Error",
            status: 500,
            instance: "/api/v1/auth/logout",
          },
          { status: 500 },
        ),
      ),
    );
    render(<Toaster />);
    await openMenu(makeMe());

    await userEvent.click(screen.getByRole("menuitem", { name: "Sign out" }));

    expect(
      await screen.findByText("Couldn't sign you out. Try again."),
    ).toBeVisible();
    expect(hardNavigate).not.toHaveBeenCalled();
  });
});
