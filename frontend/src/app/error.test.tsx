import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import RootError from "./error";

vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh: vi.fn() }) }));

describe("the root error page", () => {
  it("says ACME Pay couldn't load and tries again", async () => {
    const retry = vi.fn();
    render(<RootError error={new Error("fetch failed")} retry={retry} />);

    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("ACME Pay couldn't load");
    expect(alert).toHaveTextContent("We couldn't reach the server.");
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));

    expect(retry).toHaveBeenCalledOnce();
  });
});
