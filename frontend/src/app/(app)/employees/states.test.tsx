import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import EmployeeLoading from "./[id]/loading";
import EmployeeNotFound from "./[id]/not-found";
import DirectoryLoading from "./loading";

describe("while the directory loads", () => {
  it("says it is loading, in the shape of the search, filters and rows", () => {
    const { container } = render(<DirectoryLoading />);

    expect(screen.getByRole("status")).toHaveTextContent("Loading employees…");
    expect(container.firstElementChild).toHaveAttribute("aria-busy", "true");
    // Table rows from 640 px, list rows below: the same switch as the real list.
    expect(container.querySelector("[data-slot=rows-table]")).toHaveClass(
      "hidden",
      "sm:block",
    );
    expect(container.querySelector("[data-slot=rows-list]")).toHaveClass(
      "sm:hidden",
    );
  });
});

describe("while an employee loads", () => {
  it("says it is loading, in the shape of the title and sections", () => {
    const { container } = render(<EmployeeLoading />);

    expect(screen.getByRole("status")).toHaveTextContent(
      "Loading the employee…",
    );
    expect(container.firstElementChild).toHaveAttribute("aria-busy", "true");
  });
});

describe("an employee that doesn't exist", () => {
  it("says so and leads back to the directory", () => {
    render(<EmployeeNotFound />);

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: "We can't find this employee",
      }),
    ).toBeVisible();
    expect(
      screen.getByRole("link", { name: "Back to employees" }),
    ).toHaveAttribute("href", "/employees");
  });
});
