import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import AppError from "./error";

vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh: vi.fn() }) }));

describe("the (app) error page", () => {
  it("says the page couldn't load and tries the page again", async () => {
    const retry = vi.fn();
    render(<AppError error={new Error("boom")} retry={retry} />);

    expect(screen.getByRole("alert")).toHaveTextContent(
      "This page couldn't load",
    );
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));

    expect(retry).toHaveBeenCalledOnce();
  });
});
