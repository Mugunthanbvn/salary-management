import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Button } from "@/components/ui/button";

import { EmptyState, Forbidden } from "./index";

describe("EmptyState", () => {
  it("explains why there is nothing and offers the next action", () => {
    render(
      <EmptyState
        title="No employees match these filters"
        action={<Button>Clear filters</Button>}
      >
        Try fewer filters.
      </EmptyState>,
    );

    expect(screen.getByText("No employees match these filters")).toBeVisible();
    expect(screen.getByText("Try fewer filters.")).toBeVisible();
    expect(screen.getByRole("button", { name: "Clear filters" })).toBeVisible();
  });
});

describe("Forbidden", () => {
  it("says the page is not for this person and links back to Insights", () => {
    render(<Forbidden />);

    expect(
      screen.getByRole("heading", { name: "You don't have access to this" }),
    ).toBeVisible();
    expect(
      screen.getByRole("link", { name: "Go to Insights" }),
    ).toHaveAttribute("href", "/insights");
  });
});
