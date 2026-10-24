import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Button } from "./button";

describe("Button", () => {
  it("draws a link button without side padding, so it lines up with text", () => {
    render(<Button variant="link">Show all 10 countries</Button>);

    const button = screen.getByRole("button", {
      name: "Show all 10 countries",
    });
    expect(button).toHaveClass("px-0");
    expect(button).not.toHaveClass("px-4");
  });
});
