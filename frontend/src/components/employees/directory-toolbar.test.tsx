import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { makeReference, makeViewer } from "@/test/fixtures";
import { renderInApp } from "@/test/render";

import { DirectoryToolbar } from "./directory-toolbar";

const reference = makeReference();

function lastQuery(onUrlUpdate: ReturnType<typeof vi.fn>): string {
  const calls = onUrlUpdate.mock.calls as [{ queryString: string }][];
  return calls.at(-1)?.[0].queryString ?? "";
}

function desktopFilters() {
  return screen.getByRole("group", { name: "Filters" });
}

describe("search", () => {
  it("is a large search field with a label", () => {
    renderInApp(<DirectoryToolbar reference={reference} total={3} />);

    const search = screen.getByRole("searchbox", {
      name: "Search by name, employee code or email",
    });
    expect(search).toHaveAttribute("type", "search");
    expect(search).toHaveClass("font-serif", "border-b-2", "border-ink");
  });

  it("puts the search in the URL once typing pauses for 300 ms, back on page 1", async () => {
    const onUrlUpdate = vi.fn();
    renderInApp(<DirectoryToolbar reference={reference} total={3} />, {
      searchParams: "?page=4",
      onUrlUpdate,
      rateLimitFactor: 1,
    });

    await userEvent.type(screen.getByRole("searchbox"), "mül");

    await waitFor(() => expect(onUrlUpdate).toHaveBeenCalled());
    // nuqs keeps non-ASCII letters readable in the URL.
    expect(lastQuery(onUrlUpdate)).toBe("?q=mül");
    // The search and the page land together, in one update, not as two server renders.
    await new Promise((resolve) => setTimeout(resolve, 400));
    expect(onUrlUpdate).toHaveBeenCalledTimes(1);
  });

  it("writes the search and page 1 in a single URL update", async () => {
    const onUrlUpdate = vi.fn();
    renderInApp(<DirectoryToolbar reference={reference} total={3} />, {
      searchParams: "?page=4",
      onUrlUpdate,
    });
    // A busy machine: a few milliseconds pass between any two debounce timers being
    // set, so the ones a keystroke could set for q and for page never fire together.
    const realSetTimeout = globalThis.setTimeout;
    let lag = 0;
    vi.spyOn(globalThis, "setTimeout").mockImplementation((callback, ms = 0) =>
      realSetTimeout(callback, ms >= 100 ? ms + (lag += 5) : ms),
    );

    await userEvent.type(screen.getByRole("searchbox"), "mül");

    await waitFor(() => expect(onUrlUpdate).toHaveBeenCalled(), {
      timeout: 2000,
    });
    expect(lastQuery(onUrlUpdate)).toBe("?q=mül");
  });

  it("asks for a second character before it searches", async () => {
    renderInApp(<DirectoryToolbar reference={reference} total={3} />);

    await userEvent.type(screen.getByRole("searchbox"), "m");

    expect(
      screen.getByText("Type at least 2 characters to search."),
    ).toBeVisible();
  });
});

describe("filters on a desktop", () => {
  it("adds a country from its filter button", async () => {
    const onUrlUpdate = vi.fn();
    renderInApp(<DirectoryToolbar reference={reference} total={3} />, {
      onUrlUpdate,
    });

    await userEvent.click(
      within(desktopFilters()).getByRole("button", { name: "Country: any" }),
    );
    await userEvent.click(screen.getByRole("checkbox", { name: "Germany" }));

    expect(lastQuery(onUrlUpdate)).toBe("?country=DE");
    expect(
      within(desktopFilters()).getByRole("button", {
        name: "Country: Germany",
      }),
    ).toBeVisible();
  });

  it("shows active employees by default, and can add terminated ones", async () => {
    const onUrlUpdate = vi.fn();
    renderInApp(<DirectoryToolbar reference={reference} total={3} />, {
      onUrlUpdate,
    });

    await userEvent.click(
      within(desktopFilters()).getByRole("button", { name: "Status: Active" }),
    );
    await userEvent.click(screen.getByRole("checkbox", { name: "Terminated" }));

    expect(lastQuery(onUrlUpdate)).toBe("?status=ACTIVE&status=TERMINATED");
  });

  it("clears every filter but keeps the sort", async () => {
    const onUrlUpdate = vi.fn();
    renderInApp(<DirectoryToolbar reference={reference} total={3} />, {
      searchParams: "?q=ana&country=DE&level=L3&sort=-hire_date",
      onUrlUpdate,
    });

    await userEvent.click(
      within(desktopFilters()).getByRole("button", { name: "Clear filters" }),
    );

    expect(lastQuery(onUrlUpdate)).toBe("?sort=-hire_date");
  });
});

describe("filters on a phone", () => {
  it("counts the active filters on the Filters button, which only phones show", () => {
    renderInApp(<DirectoryToolbar reference={reference} total={3} />, {
      searchParams: "?country=DE&level=L3",
    });

    const button = screen.getByRole("button", { name: "Filters (2)" });
    expect(button.closest("[data-slot=phone-filters]")).toHaveClass(
      "sm:hidden",
    );
    expect(desktopFilters()).toHaveClass("hidden", "sm:flex");
  });

  it("shows each active filter as a chip that removes it", async () => {
    const onUrlUpdate = vi.fn();
    renderInApp(<DirectoryToolbar reference={reference} total={3} />, {
      searchParams: "?country=DE&level=L3",
      onUrlUpdate,
    });

    const chips = screen.getByRole("list", { name: "Active filters" });
    expect(within(chips).getByText("Germany")).toBeVisible();
    expect(within(chips).getByText("L3 Senior")).toBeVisible();
    await userEvent.click(
      within(chips).getByRole("button", { name: "Remove Germany" }),
    );

    expect(lastQuery(onUrlUpdate)).toBe("?level=L3");
  });

  it("opens every filter in a bottom sheet", async () => {
    const onUrlUpdate = vi.fn();
    renderInApp(<DirectoryToolbar reference={reference} total={3} />, {
      onUrlUpdate,
    });

    await userEvent.click(screen.getByRole("button", { name: "Filters (0)" }));
    const sheet = screen.getByRole("dialog", { name: "Filters" });
    for (const name of [
      "Country",
      "Department",
      "Job role",
      "Level",
      "Employment type",
      "Status",
      "Currency",
    ]) {
      expect(within(sheet).getByRole("group", { name })).toBeVisible();
    }
    await userEvent.click(
      within(sheet).getByRole("checkbox", { name: "Part-time" }),
    );

    expect(lastQuery(onUrlUpdate)).toBe("?employment_type=PART_TIME");
  });
});

describe("sort", () => {
  it("sorts by name, code, hire date, country or level", async () => {
    const onUrlUpdate = vi.fn();
    renderInApp(<DirectoryToolbar reference={reference} total={3} />, {
      onUrlUpdate,
    });

    const sort = screen.getByRole("combobox", { name: "Sort by" });
    await userEvent.selectOptions(sort, "Newest hires first");

    expect(lastQuery(onUrlUpdate)).toBe("?sort=-hire_date");
  });

  it("offers no pay sort to a viewer", () => {
    renderInApp(<DirectoryToolbar reference={reference} total={3} />, {
      me: makeViewer(),
    });

    const options = within(screen.getByRole("combobox", { name: "Sort by" }))
      .getAllByRole("option")
      .map((option) => option.textContent);
    expect(options.join(" ")).not.toMatch(/pay/i);
  });

  it("disables the pay sorts for an HR manager until there is one currency, and says why", () => {
    renderInApp(<DirectoryToolbar reference={reference} total={3} />);

    expect(
      screen.getByRole("option", { name: "Base pay, highest first" }),
    ).toBeDisabled();
    expect(
      screen.getAllByText(
        "To filter or sort by pay, choose one country or currency, or compare in US dollars.",
      ).length,
    ).toBeGreaterThan(0);
  });

  it("sorts by pay in one country", async () => {
    const onUrlUpdate = vi.fn();
    renderInApp(<DirectoryToolbar reference={reference} total={3} />, {
      searchParams: "?country=DE",
      onUrlUpdate,
    });

    await userEvent.selectOptions(
      screen.getByRole("combobox", { name: "Sort by" }),
      "Base pay, highest first",
    );

    expect(lastQuery(onUrlUpdate)).toBe("?country=DE&sort=-current_base");
  });

  it("shows the default once a pay sort no longer applies", () => {
    renderInApp(<DirectoryToolbar reference={reference} total={3} />, {
      searchParams: "?country=DE&country=JP&sort=-current_base",
    });

    expect(screen.getByRole("combobox", { name: "Sort by" })).toHaveValue("");
  });
});

describe("pay bounds and the pay currency", () => {
  it("are cleared when a filter changes the currency pay is compared in", async () => {
    const onUrlUpdate = vi.fn();
    renderInApp(<DirectoryToolbar reference={reference} total={3} />, {
      searchParams: "?country=DE&salary_min=4000000",
      onUrlUpdate,
    });

    await userEvent.click(
      within(desktopFilters()).getByRole("button", { name: /^Country/ }),
    );
    await userEvent.click(screen.getByRole("checkbox", { name: "Germany" }));
    await userEvent.click(screen.getByRole("checkbox", { name: "Japan" }));

    expect(lastQuery(onUrlUpdate)).toBe("?country=JP");
  });

  it("empty the phone sheet's pay fields after Clear filters", async () => {
    renderInApp(<DirectoryToolbar reference={reference} total={3} />, {
      searchParams: "?country=DE&salary_min=4000000",
    });

    await userEvent.click(screen.getByRole("button", { name: /^Filters/ }));
    const sheet = screen.getByRole("dialog", { name: "Filters" });
    const from = () => within(sheet).getByRole("textbox", { name: /^From/ });
    expect(from()).toHaveValue("40000");
    await userEvent.click(
      within(sheet).getByRole("button", { name: "Clear filters" }),
    );

    await waitFor(() => expect(from()).toHaveValue(""));
  });
});

describe("the pay range", () => {
  async function openPay(label = "Pay: any") {
    await userEvent.click(
      within(desktopFilters()).getByRole("button", { name: label }),
    );
    return screen.getByRole("dialog", { name: "Pay" });
  }

  it("filters by yearly pay typed in major units, sent in minor units", async () => {
    const onUrlUpdate = vi.fn();
    renderInApp(<DirectoryToolbar reference={reference} total={3} />, {
      searchParams: "?country=DE",
      onUrlUpdate,
    });

    const pay = await openPay();
    const from = within(pay).getByRole("textbox", {
      name: "From (EUR a year)",
    });
    expect(from).toHaveAttribute("inputmode", "decimal");
    await userEvent.type(from, "40,000");
    await userEvent.type(
      within(pay).getByRole("textbox", { name: "To (EUR a year)" }),
      "60000.50",
    );
    await userEvent.click(within(pay).getByRole("button", { name: "Apply" }));

    expect(lastQuery(onUrlUpdate)).toBe(
      "?country=DE&salary_min=4000000&salary_max=6000050",
    );
  });

  it("refuses more decimals than the currency has", async () => {
    const onUrlUpdate = vi.fn();
    renderInApp(<DirectoryToolbar reference={reference} total={3} />, {
      searchParams: "?country=DE",
      onUrlUpdate,
    });

    const pay = await openPay();
    await userEvent.type(
      within(pay).getByRole("textbox", { name: "From (EUR a year)" }),
      "12.345",
    );
    await userEvent.click(within(pay).getByRole("button", { name: "Apply" }));

    expect(
      within(pay).getByText("12.345 has more decimals than EUR allows"),
    ).toBeVisible();
    expect(onUrlUpdate).not.toHaveBeenCalled();
  });

  it("can't be used across currencies until pay is compared in US dollars", async () => {
    const onUrlUpdate = vi.fn();
    renderInApp(<DirectoryToolbar reference={reference} total={3} />, {
      searchParams: "?country=DE&country=JP",
      onUrlUpdate,
    });

    const pay = await openPay();
    expect(within(pay).getByRole("textbox", { name: /^From/ })).toBeDisabled();
    await userEvent.click(
      within(pay).getByRole("radio", { name: "US dollars" }),
    );

    expect(lastQuery(onUrlUpdate)).toBe(
      "?country=DE&country=JP&salary_basis=usd",
    );
    expect(
      within(pay).getByRole("textbox", { name: "From (USD a year)" }),
    ).toBeEnabled();
  });

  it("is not there for a viewer, and neither are the pay toggles", () => {
    renderInApp(<DirectoryToolbar reference={reference} total={3} />, {
      me: makeViewer(),
      searchParams: "?country=DE",
    });

    expect(screen.queryByRole("button", { name: /^Pay/ })).toBeNull();
    expect(screen.queryByRole("group", { name: "Pay shown" })).toBeNull();
    expect(screen.queryByRole("group", { name: "Period" })).toBeNull();
  });
});

describe("the pay toggles", () => {
  it("switch between base and total pay, a year or a month", async () => {
    const onUrlUpdate = vi.fn();
    renderInApp(<DirectoryToolbar reference={reference} total={3} />, {
      onUrlUpdate,
    });

    const shown = screen.getByRole("group", { name: "Pay shown" });
    expect(within(shown).getByRole("button", { name: "Base" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    await userEvent.click(within(shown).getByRole("button", { name: "Total" }));
    await userEvent.click(
      within(screen.getByRole("group", { name: "Period" })).getByRole(
        "button",
        {
          name: "A month",
        },
      ),
    );

    expect(lastQuery(onUrlUpdate)).toBe("?comp=total&period=monthly");
  });
});
