/**
 * The API's enum values (docs/glossary.md §2) as runtime lists, for URL parsers and
 * forms, and how each is written on screen. Display only: the values come from the
 * generated types, so a renamed value fails the type check here.
 */
import type { components } from "@/lib/api/schema";

type Level = components["schemas"]["Level"];
type EmploymentType = components["schemas"]["EmploymentType"];
type EmployeeStatus = components["schemas"]["EmployeeStatus"];
type SalaryReason = components["schemas"]["SalaryReason"];
type ComponentType = components["schemas"]["ComponentType"];

export const LEVELS = [
  "L1",
  "L2",
  "L3",
  "L4",
  "L5",
  "L6",
] as const satisfies readonly Level[];

export const EMPLOYMENT_TYPES = [
  "FULL_TIME",
  "PART_TIME",
  "CONTRACTOR",
] as const satisfies readonly EmploymentType[];

export const EMPLOYEE_STATUSES = [
  "ACTIVE",
  "TERMINATED",
] as const satisfies readonly EmployeeStatus[];

export const COMPONENT_TYPES = [
  "ALLOWANCE",
  "BONUS_TARGET",
] as const satisfies readonly ComponentType[];

export const EMPLOYMENT_TYPE_LABELS: Record<EmploymentType, string> = {
  FULL_TIME: "Full-time",
  PART_TIME: "Part-time",
  CONTRACTOR: "Contractor",
};

export const STATUS_LABELS: Record<EmployeeStatus, string> = {
  ACTIVE: "Active",
  TERMINATED: "Terminated",
};

/** How a salary record's reason reads in the timeline: "Merit raise on 1 Apr 2025". */
export const REASON_LABELS: Record<SalaryReason, string> = {
  HIRE: "Hired",
  PROMOTION: "Promotion",
  MERIT: "Merit raise",
  MARKET_ADJUSTMENT: "Market adjustment",
  CORRECTION: "Correction",
};

export const COMPONENT_TYPE_LABELS: Record<ComponentType, string> = {
  ALLOWANCE: "Allowance",
  BONUS_TARGET: "Bonus target",
};
