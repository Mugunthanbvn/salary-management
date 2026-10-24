import { describe, expect, it } from "vitest";

import { makeReference } from "@/test/fixtures";

import {
  hasFilters,
  loadDirectoryParams,
  salaryCurrency,
  serializeDirectory,
  toListQuery,
  withPayBoundsChecked,
} from "./directory-params";

const reference = makeReference();

describe("hasFilters", () => {
  const hr = { canReadSalaries: true, reference };

  it("counts pay bounds the list is filtered by", () => {
    expect(
      hasFilters(loadDirectoryParams("?country=DE&salary_min=1"), hr),
    ).toBe(true);
    expect(hasFilters(loadDirectoryParams("?salary_min=1"), hr)).toBe(false);
  });

  it("ignores pay bounds the API isn't sent: across currencies, or for a viewer", () => {
    expect(
      hasFilters(loadDirectoryParams("?salary_min=1"), {
        canReadSalaries: true,
        reference,
      }),
    ).toBe(false);
    expect(
      hasFilters(loadDirectoryParams("?salary_basis=usd&salary_min=1"), {
        canReadSalaries: false,
        reference,
      }),
    ).toBe(false);
  });
});

describe("withPayBoundsChecked", () => {
  it("clears pay bounds when the pay currency would change (€40,000 is not ¥4,000,000)", () => {
    const state = loadDirectoryParams("?country=DE&salary_min=4000000");

    expect(withPayBoundsChecked(state, { country: ["JP"] }, reference)).toEqual(
      {
        country: ["JP"],
        salary_min: null,
        salary_max: null,
      },
    );
  });

  it("keeps them while the currency stays the same", () => {
    const state = loadDirectoryParams("?country=DE&salary_min=4000000");

    expect(
      withPayBoundsChecked(
        state,
        { country: ["DE", "FR"], currency: ["EUR"] },
        reference,
      ),
    ).toEqual({
      country: ["DE", "FR"],
      currency: ["EUR"],
    });
  });
});

function sortedEntries(query: string): [string, string][] {
  return [...new URLSearchParams(query).entries()].sort(([a, x], [b, y]) =>
    a === b ? x.localeCompare(y) : a.localeCompare(b),
  );
}

describe("the directory's URL state", () => {
  const url =
    "?q=m%C3%BCller&country=DE&country=FR&department_id=1&job_role_id=17&level=L3" +
    "&employment_type=FULL_TIME&status=ACTIVE&status=TERMINATED&currency=EUR" +
    "&salary_min=4000000&salary_max=6000000&salary_basis=usd&comp=total" +
    "&sort=-current_base&page=2&page_size=50&period=monthly";

  it("loads every filter, sort and page from the URL, with the API's names", () => {
    expect(loadDirectoryParams(url)).toEqual({
      q: "müller",
      country: ["DE", "FR"],
      department_id: [1],
      job_role_id: [17],
      level: ["L3"],
      employment_type: ["FULL_TIME"],
      status: ["ACTIVE", "TERMINATED"],
      currency: ["EUR"],
      salary_min: 4_000_000,
      salary_max: 6_000_000,
      salary_basis: "usd",
      comp: "total",
      sort: "-current_base",
      page: 2,
      page_size: 50,
      period: "monthly",
    });
  });

  it("writes the same state back to the same URL", () => {
    const state = loadDirectoryParams(url);

    expect(sortedEntries(serializeDirectory(state))).toEqual(
      sortedEntries(url),
    );
  });

  it("leaves defaults out of the URL: active employees, page 1 of 25, base pay a year", () => {
    const state = loadDirectoryParams("");

    expect(state).toMatchObject({
      q: "",
      status: ["ACTIVE"],
      page: 1,
      page_size: 25,
      comp: "base",
      period: "annual",
      salary_basis: "local",
      sort: null,
    });
    expect(serializeDirectory(state)).toBe("");
  });

  it("ignores values the API doesn't know, rather than failing", () => {
    expect(
      loadDirectoryParams("?level=L9&status=GONE&page_size=1000&comp=bonus"),
    ).toMatchObject({
      level: [],
      status: ["ACTIVE"],
      page_size: 25,
      comp: "base",
    });
  });
});

describe("salaryCurrency", () => {
  it.each([
    { url: "?salary_basis=usd&country=DE&country=JP", currency: "USD" },
    { url: "?currency=JPY", currency: "JPY" },
    { url: "?country=IN", currency: "INR" },
    { url: "?country=DE&country=FR&currency=EUR", currency: "EUR" },
    { url: "?country=DE&country=JP", currency: null },
    { url: "", currency: null },
  ])("for $url pay is compared in $currency", ({ url, currency }) => {
    expect(salaryCurrency(loadDirectoryParams(url), reference)).toBe(currency);
  });
});

describe("toListQuery", () => {
  const hr = { canReadSalaries: true, reference };
  const viewer = { canReadSalaries: false, reference };

  it("sends the filters, sort and page under the API's names, and never the period", () => {
    const state = loadDirectoryParams(
      "?q=müller&country=DE&level=L3&status=ACTIVE&sort=-hire_date&page=2&page_size=50&period=monthly",
    );

    expect(toListQuery(state, hr)).toEqual({
      q: "müller",
      country: ["DE"],
      level: ["L3"],
      status: ["ACTIVE"],
      sort: "-hire_date",
      page: 2,
      page_size: 50,
    });
  });

  it("waits for two characters before searching, as the API requires", () => {
    const state = loadDirectoryParams("?q=m");

    expect(toListQuery(state, hr)).not.toHaveProperty("q");
  });

  it("sends a salary range and salary sort for one country to an HR manager", () => {
    const state = loadDirectoryParams(
      "?country=DE&salary_min=4000000&salary_max=6000000&comp=total&sort=-current_total",
    );

    expect(toListQuery(state, hr)).toMatchObject({
      country: ["DE"],
      salary_min: 4_000_000,
      salary_max: 6_000_000,
      comp: "total",
      sort: "-current_total",
    });
  });

  it("sends salary_basis=usd with a range across currencies", () => {
    const state = loadDirectoryParams(
      "?country=DE&country=JP&salary_basis=usd&salary_min=5000000",
    );

    expect(toListQuery(state, hr)).toMatchObject({
      salary_basis: "usd",
      salary_min: 5_000_000,
    });
  });

  it("drops a salary range or sort across currencies, which the API would refuse", () => {
    const state = loadDirectoryParams(
      "?country=DE&country=JP&salary_min=5000000&sort=-current_base,last_name",
    );

    const query = toListQuery(state, hr);

    expect(query).not.toHaveProperty("salary_min");
    expect(query.sort).toBe("last_name");
  });

  it("never sends a viewer's salary filters or sorts (the API answers 403)", () => {
    const state = loadDirectoryParams(
      "?country=DE&salary_min=4000000&salary_basis=usd&comp=total&sort=-current_base",
    );

    expect(toListQuery(state, viewer)).toEqual({
      country: ["DE"],
      status: ["ACTIVE"],
      page: 1,
      page_size: 25,
    });
  });

  it("drops sort fields the API doesn't allow", () => {
    const state = loadDirectoryParams("?sort=salary,-employee_code");

    expect(toListQuery(state, hr).sort).toBe("-employee_code");
  });
});
