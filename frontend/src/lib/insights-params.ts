/**
 * The insights and pay-equity screens' state in the URL (docs/13-frontend-ux.md §3.2), shared
 * by the Server Components that call the API and the Client Components that change it.
 * Keys are the API's query parameter names; `period` is the one UI-only key.
 */
import {
  createLoader,
  createSerializer,
  parseAsBoolean,
  parseAsInteger,
  parseAsNativeArrayOf,
  parseAsString,
  parseAsStringLiteral,
  type inferParserType,
} from "nuqs/server";

import type { components, paths } from "@/lib/api/schema";
import {
  EMPLOYEE_STATUSES,
  EMPLOYMENT_TYPES,
  EMPLOYMENT_TYPE_LABELS,
  STATUS_LABELS,
} from "@/lib/labels";

type EmploymentType = components["schemas"]["EmploymentType"];
type EmployeeStatus = components["schemas"]["EmployeeStatus"];
export type InsightQuery = NonNullable<
  paths["/api/v1/insights/overview"]["get"]["parameters"]["query"]
>;

export const COMPS = ["base", "total"] as const;
export const PERIODS = ["annual", "monthly"] as const;
export const DIRECTIONS = ["top", "bottom"] as const;

export const insightsParsers = {
  // One country at a time: job titles and top earners only mean something in one market.
  country: parseAsString,
  department_id: parseAsInteger,
  comp: parseAsStringLiteral(COMPS).withDefault("base"),
  // UI only: amounts are annual; "monthly" shows annual ÷ 12 (lib/money.ts).
  period: parseAsStringLiteral(PERIODS).withDefault("annual"),
  // The API's population defaults (docs/09 §2.1), made visible by the population chip.
  employment_type: parseAsNativeArrayOf(
    parseAsStringLiteral(EMPLOYMENT_TYPES),
  ).withDefault(["FULL_TIME"]),
  status: parseAsNativeArrayOf(
    parseAsStringLiteral(EMPLOYEE_STATUSES),
  ).withDefault(["ACTIVE"]),
  split_by_level: parseAsBoolean.withDefault(false),
  direction: parseAsStringLiteral(DIRECTIONS).withDefault("top"),
};

export type InsightsState = inferParserType<typeof insightsParsers>;

/** The state in a URL, a query string or the page's `searchParams` (also a Promise). */
export const loadInsightsParams = createLoader(insightsParsers);

/** The query string for a state; defaults are left out. */
export const serializeInsights = createSerializer(insightsParsers);

export const payEquityParsers = {
  country: parseAsString,
  department_id: parseAsInteger,
};

export type PayEquityState = inferParserType<typeof payEquityParsers>;
export const loadPayEquityParams = createLoader(payEquityParsers);
export const serializePayEquity = createSerializer(payEquityParsers);

/** The common insight filters for the API: the population, the filters and `comp`. */
export function toInsightQuery(state: InsightsState): InsightQuery {
  return {
    ...(state.country ? { country: [state.country] } : {}),
    ...(state.department_id !== null
      ? { department_id: [state.department_id] }
      : {}),
    employment_type: state.employment_type,
    status: state.status,
    comp: state.comp,
  };
}

/** The population chip's text: "Full-time · Active". */
export function populationLabel(
  types: EmploymentType[],
  statuses: EmployeeStatus[],
): string {
  const typeText = types.map((type) => EMPLOYMENT_TYPE_LABELS[type]).join(", ");
  const statusText = statuses.map((status) => STATUS_LABELS[status]).join(", ");
  return `${typeText} · ${statusText}`;
}
