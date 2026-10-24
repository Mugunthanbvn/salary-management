import type { components } from "@/lib/api/schema";

type S = components["schemas"];
type Stats = S["Stats"];
type Population = S["Population"];

/** The API's default population (full-time, active, base pay). */
export function makePopulation(
  overrides: Partial<Population> = {},
): Population {
  return {
    comp: "base",
    country: [],
    department_id: [],
    job_role_id: [],
    level: [],
    employment_type: ["FULL_TIME"],
    status: ["ACTIVE"],
    ...overrides,
  };
}

/** A stats object as an HR manager sees it: every figure, min and max included. */
export function makeStats(overrides: Partial<Stats> = {}): Stats {
  return {
    count: 702,
    min: 3_900_000,
    p25: 4_800_000,
    median: 5_400_000,
    mean: 5_520_000,
    p75: 6_300_000,
    max: 16_800_000,
    currency: "EUR",
    suppressed: false,
    ...overrides,
  };
}

/** A group a viewer may not see: fewer than 5 people, so every figure is null. */
export function suppressedStats(currency = "EUR"): Stats {
  return {
    count: null,
    min: null,
    p25: null,
    median: null,
    mean: null,
    p75: null,
    max: null,
    currency,
    suppressed: true,
  };
}

/** The same stats as a viewer sees them: min and max are always null. */
export function viewerStats(stats: Stats): Stats {
  return { ...stats, min: null, max: null };
}

export function makeOverview(
  overrides: Partial<S["Overview"]> = {},
): S["Overview"] {
  return {
    population: makePopulation(),
    currency: "USD",
    fx_as_of: "2026-10-01",
    headcount: 9012,
    total_payroll_usd: { amount_minor: 82_350_000_000, currency: "USD" },
    stats: makeStats({
      count: 9012,
      currency: "USD",
      median: 7_200_000,
    }),
    by_country: [
      {
        country_code: "DE",
        local: makeStats(),
        usd: makeStats({ currency: "USD", median: 5_832_000 }),
      },
      {
        country_code: "IN",
        local: makeStats({
          count: 2250,
          currency: "INR",
          min: 90_000_000,
          p25: 142_000_000,
          median: 186_000_000,
          mean: 190_000_000,
          p75: 248_000_000,
          max: 900_000_000,
        }),
        usd: makeStats({ count: 2250, currency: "USD", median: 2_232_000 }),
      },
    ],
    ...overrides,
  };
}

export function makeByDepartment(
  overrides: Partial<S["ByDepartment"]> = {},
): S["ByDepartment"] {
  return {
    population: makePopulation(),
    currency: "USD",
    fx_as_of: "2026-10-01",
    groups: [
      {
        department: { id: 4, name: "Customer Success" },
        stats: makeStats({ count: 840, currency: "USD", median: 5_100_000 }),
      },
      {
        department: { id: 1, name: "Engineering" },
        stats: makeStats({ count: 3150, currency: "USD", median: 9_800_000 }),
      },
    ],
    ...overrides,
  };
}

export function makeDepartmentCosts(
  overrides: Partial<S["DepartmentCosts"]> = {},
): S["DepartmentCosts"] {
  return {
    population: makePopulation(),
    currency: "USD",
    fx_as_of: "2026-10-01",
    headcount: 9012,
    suppressed: false,
    total: { amount_minor: 82_350_000_000, currency: "USD" },
    total_usd: { amount_minor: 82_350_000_000, currency: "USD" },
    groups: [
      {
        department: { id: 1, name: "Engineering" },
        headcount: 3150,
        cost: { amount_minor: 36_230_000_000, currency: "USD" },
        cost_usd: { amount_minor: 36_230_000_000, currency: "USD" },
        share_of_total: "0.4400",
        suppressed: false,
      },
      {
        department: { id: 4, name: "Customer Success" },
        headcount: 840,
        cost: { amount_minor: 5_760_000_000, currency: "USD" },
        cost_usd: { amount_minor: 5_760_000_000, currency: "USD" },
        share_of_total: "0.0700",
        suppressed: false,
      },
    ],
    ...overrides,
  };
}

export function makeByJobTitle(
  overrides: Partial<S["ByJobTitle"]> = {},
): S["ByJobTitle"] {
  return {
    population: makePopulation({ country: ["DE"] }),
    currency: "EUR",
    split_by_level: false,
    groups: [
      {
        job_role: { id: 17, title: "Customer Success Manager" },
        level: null,
        stats: makeStats({ count: 41, median: 4_800_000 }),
      },
      {
        job_role: { id: 5, title: "Software Engineer" },
        level: null,
        stats: makeStats({ count: 118, median: 9_040_000 }),
      },
    ],
    ...overrides,
  };
}

export function makeTopEarners(
  overrides: Partial<S["TopEarners"]> = {},
): S["TopEarners"] {
  return {
    population: makePopulation({ country: ["DE"] }),
    country_code: "DE",
    currency: "EUR",
    direction: "top",
    n: 10,
    items: [
      {
        employee_id: 2210,
        employee_code: "ACME-002210",
        first_name: "Katharina",
        last_name: "Vogel",
        job_role: { id: 9, title: "Engineering Manager" },
        level: "L6",
        department: { id: 1, name: "Engineering" },
        amount: { amount_minor: 16_800_000, currency: "EUR" },
      },
    ],
    ...overrides,
  };
}

export const THRESHOLDS: S["Thresholds"] = {
  low: "0.80",
  high: "1.20",
  rollup: "0.95",
};

export function makePayEquitySummary(
  overrides: Partial<S["PayEquitySummary"]> = {},
): S["PayEquitySummary"] {
  return {
    employees_evaluated: 702,
    employees_without_band: 0,
    employees_not_full_time: 48,
    employees_flagged_underpaid: 31,
    employees_flagged_overpaid: 12,
    suppressed: false,
    ...overrides,
  };
}

export function makeCohort(
  overrides: Partial<S["CohortEquity"]> = {},
): S["CohortEquity"] {
  return {
    job_role: { id: 17, title: "Customer Success Manager" },
    level: "L2",
    country_code: "DE",
    department: { id: 4, name: "Customer Success" },
    stats: makeStats({
      count: 18,
      min: 3_900_000,
      p25: 4_300_000,
      median: 4_700_000,
      mean: 4_650_000,
      p75: 4_900_000,
      max: 5_400_000,
    }),
    band: { min: 4_176_000, mid: 5_220_000, max: 6_264_000, currency: "EUR" },
    median_compa_ratio: "0.90",
    underpaid_count: 5,
    overpaid_count: 0,
    suppressed: false,
    ...overrides,
  };
}

export function makePayEquityCohorts(
  overrides: Partial<S["PayEquityCohorts"]> = {},
): S["PayEquityCohorts"] {
  return {
    view: "cohorts",
    population: makePopulation({ country: ["DE"] }),
    thresholds: THRESHOLDS,
    cohorts: [
      makeCohort(),
      makeCohort({
        job_role: { id: 5, title: "Software Engineer" },
        level: "L3",
        department: { id: 1, name: "Engineering" },
        stats: makeStats({
          count: 118,
          p25: 8_400_000,
          median: 9_040_000,
          p75: 9_700_000,
        }),
        band: {
          min: 7_200_000,
          mid: 9_000_000,
          max: 10_800_000,
          currency: "EUR",
        },
        median_compa_ratio: "1.00",
        underpaid_count: 2,
        overpaid_count: 3,
      }),
    ],
    summary: makePayEquitySummary(),
    ...overrides,
  };
}

export function makeDepartmentEquity(
  overrides: Partial<S["DepartmentEquity"]> = {},
): S["DepartmentEquity"] {
  return {
    department: { id: 1, name: "Engineering" },
    count: 287,
    median_compa_ratio: "1.00",
    mean_compa_ratio: "1.01",
    pct_below_band: "0.04",
    underpaid_count: 11,
    overpaid_count: 9,
    below_threshold: false,
    suppressed: false,
    ...overrides,
  };
}

export function makePayEquityDepartments(
  overrides: Partial<S["PayEquityDepartments"]> = {},
): S["PayEquityDepartments"] {
  return {
    view: "departments",
    population: makePopulation({ country: ["DE"] }),
    country_code: "DE",
    thresholds: THRESHOLDS,
    groups: [
      makeDepartmentEquity({
        department: { id: 4, name: "Customer Success" },
        count: 41,
        median_compa_ratio: "0.93",
        mean_compa_ratio: "0.93",
        pct_below_band: "0.29",
        underpaid_count: 12,
        overpaid_count: 0,
        below_threshold: true,
      }),
      makeDepartmentEquity(),
    ],
    summary: makePayEquitySummary(),
    ...overrides,
  };
}

export function makeCohortMembers(
  overrides: Partial<S["CohortMembers"]> = {},
): S["CohortMembers"] {
  return {
    population: makePopulation({ country: ["DE"] }),
    job_role: { id: 17, title: "Customer Success Manager" },
    level: "L2",
    country_code: "DE",
    department: { id: 4, name: "Customer Success" },
    currency: "EUR",
    band: { min: 4_176_000, mid: 5_220_000, max: 6_264_000, currency: "EUR" },
    thresholds: THRESHOLDS,
    members: [
      {
        employee_id: 3412,
        employee_code: "ACME-003412",
        first_name: "Lukas",
        last_name: "Weber",
        employment_type: "FULL_TIME",
        base: { amount_minor: 3_650_000, currency: "EUR" },
        compa_ratio: "0.70",
        flag: "UNDERPAID",
        no_compa_ratio_reason: null,
      },
      {
        employee_id: 3589,
        employee_code: "ACME-003589",
        first_name: "Hannah",
        last_name: "Meyer",
        employment_type: "FULL_TIME",
        base: { amount_minor: 5_300_000, currency: "EUR" },
        compa_ratio: "1.02",
        flag: "IN_BAND",
        no_compa_ratio_reason: null,
      },
    ],
    ...overrides,
  };
}
