import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  Sheet,
  SheetContent,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "./sheet";

describe("Sheet", () => {
  it("keeps its pinned header and footer above the content that scrolls under them", () => {
    render(
      <Sheet open>
        <SheetContent side="bottom">
          <SheetHeader data-testid="header">
            <SheetTitle>Filters</SheetTitle>
          </SheetHeader>
          <input aria-label="From (a year)" />
          <SheetFooter data-testid="footer">Show results</SheetFooter>
        </SheetContent>
      </Sheet>,
    );

    // jsdom has no painting: check the classes that pin them and lift them above.
    expect(screen.getByTestId("header")).toHaveClass("sticky", "top-0", "z-10");
    expect(screen.getByTestId("footer")).toHaveClass(
      "sticky",
      "bottom-0",
      "z-10",
    );
  });
});
