import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import {
  makeEmployeeListItem,
  makeEmployeePage,
  makeMaskedListItem,
  makeReference,
  makeViewer,
} from "@/test/fixtures";
import { renderInApp } from "@/test/render";

import { EmployeeResults } from "./employee-results";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn(), push: vi.fn() }),
}));

const reference = makeReference();

function table() {
  return screen.getByRole("table", { name: /Employees/ });
}

function cards() {
  return screen.getByRole("list", { name: "Employees" });
}

describe("EmployeeResults for an HR manager", () => {
  it("shows base pay a year in its own right-aligned column", () => {
    renderInApp(
      <EmployeeResults page={makeEmployeePage()} reference={reference} />,
    );

    const header = within(table()).getByRole("columnheader", {
      name: "Base pay a year",
    });
    expect(header).toHaveClass("text-right");
    const row = within(table()).getByRole("row", { name: /Lena Müller/ });
    expect(within(row).getByText("€47,500")).toBeVisible();
    expect(within(cards()).getByText("€47,500")).toBeVisible();
  });

  it("shows a month's pay when the period is monthly (display only)", () => {
    renderInApp(
      <EmployeeResults page={makeEmployeePage()} reference={reference} />,
      {
        searchParams: "?period=monthly",
      },
    );

    expect(
      within(table()).getByRole("columnheader", { name: "Base pay a month" }),
    ).toBeVisible();
    // €47,500 ÷ 12 = €3,958.333…, shown half-even to the cent.
    expect(within(table()).getByText("€3,958.33")).toBeVisible();
  });

  it("shows total pay when total is chosen", () => {
    renderInApp(
      <EmployeeResults page={makeEmployeePage()} reference={reference} />,
      {
        searchParams: "?comp=total",
      },
    );

    expect(
      within(table()).getByRole("columnheader", { name: "Total pay a year" }),
    ).toBeVisible();
    expect(within(table()).getByText("€51,820")).toBeVisible();
  });
});

describe("EmployeeResults for a viewer", () => {
  it("has no pay column and no amounts at all", () => {
    const page = makeEmployeePage([makeMaskedListItem()]);

    renderInApp(<EmployeeResults page={page} reference={reference} />, {
      me: makeViewer(),
    });

    const headers = within(table())
      .getAllByRole("columnheader")
      .map((header) => header.textContent);
    expect(headers.join(" ")).not.toMatch(/pay/i);
    expect(screen.queryByText(/€/)).toBeNull();
  });
});

describe("EmployeeResults layout", () => {
  it("is a card list below 640 px and a table from 640 px, never both", () => {
    renderInApp(
      <EmployeeResults page={makeEmployeePage()} reference={reference} />,
    );

    // jsdom has no layout: check the breakpoint classes that switch them.
    expect(cards()).toHaveClass("sm:hidden");
    expect(table().closest("[data-slot=results-table]")).toHaveClass(
      "hidden",
      "sm:block",
    );
  });

  it("links every row and card to the employee's page", () => {
    renderInApp(
      <EmployeeResults page={makeEmployeePage()} reference={reference} />,
    );

    for (const region of [table(), cards()]) {
      expect(
        within(region).getByRole("link", { name: /Lena Müller/ }),
      ).toHaveAttribute("href", "/employees/2210");
    }
  });

  it("shows the role, level, department, country and code of each employee", () => {
    renderInApp(
      <EmployeeResults page={makeEmployeePage()} reference={reference} />,
    );

    const card = within(cards()).getByRole("listitem");
    expect(card).toHaveTextContent("Customer Success Manager, L2");
    expect(card).toHaveTextContent("Germany, ACME-002210");
    const row = within(table()).getByRole("row", { name: /Lena Müller/ });
    expect(row).toHaveTextContent("Customer Success");
    expect(row).toHaveTextContent("Germany");
  });

  it("marks a terminated employee with the word, not only grey text", () => {
    const page = makeEmployeePage([
      makeEmployeeListItem({ status: "TERMINATED" }),
    ]);

    renderInApp(<EmployeeResults page={page} reference={reference} />);

    expect(within(table()).getByText("Terminated")).toBeVisible();
    expect(within(cards()).getByText("Terminated")).toBeVisible();
  });
});

describe("EmployeeResults paging", () => {
  const items = [makeEmployeeListItem()];

  it("says which rows are shown, and links to the pages around this one", () => {
    const page = makeEmployeePage(items, {
      page: 2,
      page_size: 25,
      total: 9700,
    });

    renderInApp(<EmployeeResults page={page} reference={reference} />, {
      searchParams: "?country=DE&page=2",
    });

    const pages = screen.getByRole("navigation", { name: "Pages" });
    expect(pages).toHaveTextContent("26–50 of 9,700");
    expect(
      within(pages).getByRole("link", { name: "Previous" }),
    ).toHaveAttribute("href", "/employees?country=DE");
    expect(within(pages).getByRole("link", { name: "Next" })).toHaveAttribute(
      "href",
      "/employees?country=DE&page=3",
    );
  });

  it("has no Previous on the first page and no Next on the last", () => {
    const page = makeEmployeePage(items, { page: 1, page_size: 25, total: 1 });

    renderInApp(<EmployeeResults page={page} reference={reference} />);

    const pages = screen.getByRole("navigation", { name: "Pages" });
    expect(pages).toHaveTextContent("1–1 of 1");
    expect(within(pages).queryByRole("link", { name: "Previous" })).toBeNull();
    expect(within(pages).queryByRole("link", { name: "Next" })).toBeNull();
  });

  it("changes the page size from the desktop picker, back to page 1", async () => {
    const onUrlUpdate = vi.fn();
    const page = makeEmployeePage(items, {
      page: 3,
      page_size: 25,
      total: 9700,
    });
    renderInApp(<EmployeeResults page={page} reference={reference} />, {
      searchParams: "?page=3",
      onUrlUpdate,
    });

    const picker = screen.getByRole("combobox", { name: "Rows per page" });
    expect(picker.closest("[data-slot=page-size]")).toHaveClass(
      "hidden",
      "sm:flex",
    );
    await userEvent.selectOptions(picker, "100");

    expect(onUrlUpdate).toHaveBeenLastCalledWith(
      expect.objectContaining({ queryString: "?page_size=100" }),
    );
  });
});

describe("EmployeeResults when nothing matches", () => {
  it("explains and offers to clear the filters", async () => {
    const onUrlUpdate = vi.fn();
    const page = makeEmployeePage([], { total: 0 });
    renderInApp(<EmployeeResults page={page} reference={reference} />, {
      searchParams: "?q=zzz&country=JP&level=L6&period=monthly",
      onUrlUpdate,
    });

    expect(screen.getByText("No employees match these filters")).toBeVisible();
    await userEvent.click(
      screen.getByRole("button", { name: "Clear filters" }),
    );

    expect(onUrlUpdate).toHaveBeenLastCalledWith(
      expect.objectContaining({ queryString: "?period=monthly" }),
    );
    expect(screen.queryByRole("table")).toBeNull();
  });

  it("offers the first page when the page is past the end", () => {
    const page = makeEmployeePage([], { page: 9, total: 30 });

    renderInApp(<EmployeeResults page={page} reference={reference} />, {
      searchParams: "?page=9",
    });

    expect(
      screen.getByText("This page is past the end of the list"),
    ).toBeVisible();
    expect(
      screen.getByRole("link", { name: "Go to the first page" }),
    ).toHaveAttribute("href", "/employees");
  });
});
