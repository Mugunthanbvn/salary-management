import {
  createLoader,
  createSerializer,
  parseAsInteger,
  parseAsString,
} from "nuqs/server";

import type { components } from "@/lib/api/schema";

type EmploymentType = components["schemas"]["EmploymentType"];
type EmployeeStatus = components["schemas"]["EmployeeStatus"];

export const insightsParsers = {};
export const loadInsightsParams = createLoader(insightsParsers);
export const serializeInsights = createSerializer(insightsParsers);

export const payEquityParsers = {
  country: parseAsString,
  department_id: parseAsInteger,
};
export const loadPayEquityParams = createLoader(payEquityParsers);
export const serializePayEquity = createSerializer(payEquityParsers);

export function toInsightQuery(state: unknown): unknown {
  void state;
  throw new Error("toInsightQuery is not implemented yet");
}

export function populationLabel(
  types: EmploymentType[],
  statuses: EmployeeStatus[],
): string {
  void [types, statuses];
  throw new Error("populationLabel is not implemented yet");
}
