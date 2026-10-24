import { describe, expect, it } from "vitest";

import {
  loadInsightsParams,
  loadPayEquityParams,
  populationLabel,
  serializeInsights,
  serializePayEquity,
  toInsightQuery,
} from "./insights-params";

describe("insights URL state", () => {
  it("defaults to full-time, active people, base pay, a year", () => {
    const state = loadInsightsParams("");

    expect(state).toMatchObject({
      country: null,
      department_id: null,
      comp: "base",
      period: "annual",
      employment_type: ["FULL_TIME"],
      status: ["ACTIVE"],
      split_by_level: false,
      direction: "top",
    });
  });

  it("round-trips through the URL with the API's parameter names", () => {
    const search =
      "?country=DE&department_id=4&comp=total&period=monthly&employment_type=FULL_TIME&employment_type=PART_TIME&status=ACTIVE&status=TERMINATED&split_by_level=true&direction=bottom";

    const state = loadInsightsParams(search);

    expect(serializeInsights(state)).toBe(search);
  });

  it("leaves the defaults out of the URL", () => {
    expect(
      serializeInsights(loadInsightsParams("?comp=base&period=annual")),
    ).toBe("");
  });

  it("ignores values the API would refuse", () => {
    const state = loadInsightsParams(
      "?comp=net&period=weekly&employment_type=INTERN&department_id=x",
    );

    expect(state).toMatchObject({
      comp: "base",
      period: "annual",
      employment_type: ["FULL_TIME"],
      department_id: null,
    });
  });

  it("asks the API for the population, filters and comp basis, never the period", () => {
    const state = loadInsightsParams(
      "?country=DE&department_id=4&comp=total&period=monthly",
    );

    expect(toInsightQuery(state)).toEqual({
      country: ["DE"],
      department_id: [4],
      employment_type: ["FULL_TIME"],
      status: ["ACTIVE"],
      comp: "total",
    });
  });

  it("sends no country or department when none is chosen", () => {
    expect(toInsightQuery(loadInsightsParams(""))).toEqual({
      employment_type: ["FULL_TIME"],
      status: ["ACTIVE"],
      comp: "base",
    });
  });
});

describe("pay equity URL state", () => {
  it("round-trips the country and department", () => {
    const state = loadPayEquityParams("?country=DE&department_id=4");

    expect(state).toEqual({ country: "DE", department_id: 4 });
    expect(serializePayEquity(state)).toBe("?country=DE&department_id=4");
  });
});

describe("populationLabel", () => {
  it.each([
    [["FULL_TIME"], ["ACTIVE"], "Full-time · Active"],
    [["FULL_TIME", "PART_TIME"], ["ACTIVE"], "Full-time, Part-time · Active"],
    [
      ["CONTRACTOR"],
      ["ACTIVE", "TERMINATED"],
      "Contractor · Active, Terminated",
    ],
  ] as const)("%j and %j read %s", (types, statuses, label) => {
    expect(populationLabel([...types], [...statuses])).toBe(label);
  });
});
