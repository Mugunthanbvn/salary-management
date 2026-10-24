import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { renderInApp } from "@/test/render";

import { HIDDEN_REASON, Hidden, PeriodMoney } from "./figures";

describe("Hidden", () => {
  it("shows a dash that explains itself on tap", async () => {
    const user = userEvent.setup();
    renderInApp(<Hidden />);

    const dash = screen.getByRole("button", { name: HIDDEN_REASON });
    expect(dash).toHaveTextContent("—");
    await user.click(dash);

    expect(await screen.findByRole("dialog")).toHaveTextContent(
      "Hidden to protect individual pay (fewer than 5 people)",
    );
  });
});

describe("PeriodMoney", () => {
  it("shows the API's annual amount by default", () => {
    renderInApp(<PeriodMoney amountMinor={5_400_000} currency="EUR" />);

    expect(screen.getByText("€54,000")).toBeVisible();
  });

  it("shows a twelfth of it when the URL asks for monthly", () => {
    renderInApp(<PeriodMoney amountMinor={5_400_000} currency="EUR" />, {
      searchParams: "?period=monthly",
    });

    expect(screen.getByText("€4,500")).toBeVisible();
  });

  it("is a dash when the API sent no amount", () => {
    renderInApp(<PeriodMoney amountMinor={null} currency="EUR" />);

    expect(screen.getByRole("button", { name: HIDDEN_REASON })).toBeVisible();
  });
});
