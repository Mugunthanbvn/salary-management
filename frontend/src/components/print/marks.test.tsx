import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Highlight, MarginNote, Money, RedPen, StatusWord } from "./index";

describe("printout marks", () => {
  it("Highlight marks the key figure as highlighted text", () => {
    render(
      <p>
        Paid <Highlight>US$823.5M a year</Highlight> in base pay.
      </p>,
    );

    expect(screen.getByText("US$823.5M a year").tagName).toBe("MARK");
  });

  it("RedPen and MarginNote keep their words, so meaning never rests on colour", () => {
    render(
      <>
        <RedPen>8% below its pay bands</RedPen>
        <MarginNote>Each country is shown in its own currency.</MarginNote>
      </>,
    );

    expect(screen.getByText("8% below its pay bands")).toBeVisible();
    expect(
      screen.getByText("Each country is shown in its own currency."),
    ).toBeVisible();
  });

  it.each(["problem", "notice", "plain"] as const)(
    "StatusWord says the status in words (%s tone)",
    (tone) => {
      render(<StatusWord tone={tone}>Below band</StatusWord>);

      expect(screen.getByText("Below band")).toBeVisible();
    },
  );

  // DESIGN.md: 2–3 px thick, 4–6 px offset, as in the red-pen utility (globals.css).
  it("StatusWord marks a problem with the red-pen underline", () => {
    render(<StatusWord tone="problem">Below band</StatusWord>);

    expect(screen.getByText("Below band")).toHaveClass("red-pen");
  });

  it("Money shows the amount with its currency, on one line", () => {
    render(<Money amountMinor={5_400_000} currency="EUR" />);

    const amount = screen.getByText("€54,000");
    expect(amount).toHaveClass("whitespace-nowrap");
  });
});
