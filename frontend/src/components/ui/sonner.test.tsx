import { render, screen } from "@testing-library/react";
import { toast } from "sonner";
import { describe, expect, it } from "vitest";

import { Toaster } from "./sonner";

// The phone bottom bar is 3.5rem tall plus the safe-area inset (components/shell/bottom-nav).
const ABOVE_BOTTOM_BAR = "calc(3.5rem + env(safe-area-inset-bottom) + 8px)";

describe("Toaster", () => {
  it("shows toasts above the phone bottom bar, not on top of it", async () => {
    render(<Toaster />);

    toast("Saved");
    await screen.findByText("Saved");

    const toaster = document.querySelector<HTMLElement>(
      "[data-sonner-toaster]",
    );
    // Sonner switches to its mobile offsets below 600 px; the bar shows below 640 px.
    expect(toaster?.style.getPropertyValue("--mobile-offset-bottom")).toBe(
      ABOVE_BOTTOM_BAR,
    );
    expect(toaster?.style.getPropertyValue("--offset-bottom")).toBe(
      ABOVE_BOTTOM_BAR,
    );
  });
});
