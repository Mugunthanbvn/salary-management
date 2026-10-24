import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import LoginPage from "./page";

describe("LoginPage", () => {
  it("asks for an email and a password", () => {
    render(<LoginPage />);

    expect(
      screen.getByRole("heading", { level: 1, name: "Sign in to ACME Pay" }),
    ).toBeVisible();
    expect(screen.getByLabelText("Email")).toHaveAttribute("type", "email");
    expect(screen.getByLabelText("Password")).toHaveAttribute(
      "type",
      "password",
    );
  });

  it("lists the demo accounts, without passwords, when the demo flag is on", () => {
    vi.stubEnv("NEXT_PUBLIC_SHOW_DEMO_ACCOUNTS", "true");

    render(<LoginPage />);

    const demo = screen.getByRole("region", { name: "Demo accounts" });
    const rows = within(demo)
      .getAllByRole("listitem")
      .map((item) => item.textContent);
    expect(rows).toEqual([
      "Arun, Admin: admin@acme.example",
      "Hema, HR Manager: hr@acme.example",
      "Farah, Viewer: viewer@acme.example",
    ]);
    expect(demo).toHaveTextContent(
      "The passwords are in the submission email.",
    );
  });

  it("shows no demo accounts when the demo flag is off", () => {
    vi.stubEnv("NEXT_PUBLIC_SHOW_DEMO_ACCOUNTS", "");

    render(<LoginPage />);

    expect(screen.queryByRole("region", { name: "Demo accounts" })).toBeNull();
  });
});
