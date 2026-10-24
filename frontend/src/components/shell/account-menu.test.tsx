import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import type { Me } from "@/lib/permissions";
import { makeMe } from "@/test/fixtures";

import { AccountMenu } from "./account-menu";
import { MeProvider } from "./me-context";

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
});
