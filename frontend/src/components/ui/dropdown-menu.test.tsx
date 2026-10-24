import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "./dropdown-menu";

describe("DropdownMenuItem", () => {
  // The grey focus background alone is about 1.3:1 against paper: keyboard users need the
  // blue-pen outline too (WCAG 1.4.11, docs/13-frontend-ux.md §7). jsdom can't match
  // :focus-visible, so check the item keeps the outline instead of removing it.
  it("keeps a visible blue-pen outline for keyboard focus", () => {
    render(
      <DropdownMenu open>
        <DropdownMenuTrigger>Account</DropdownMenuTrigger>
        <DropdownMenuContent>
          <DropdownMenuItem>Sign out</DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>,
    );

    const item = screen.getByRole("menuitem", { name: "Sign out" });
    expect(item).not.toHaveClass("outline-none");
    expect(item).toHaveClass(
      "focus-visible:outline-2",
      "focus-visible:outline-blue-pen",
    );
  });
});
