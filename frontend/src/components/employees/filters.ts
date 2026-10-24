import type { Nullable } from "nuqs";

import type { components } from "@/lib/api/schema";
import type { DirectoryState } from "@/lib/directory-params";
import {
  EMPLOYEE_STATUSES,
  EMPLOYMENT_TYPE_LABELS,
  STATUS_LABELS,
} from "@/lib/labels";

import { isDefaultStatus } from "./directory-state";

type ReferenceData = components["schemas"]["ReferenceData"];

export type FilterKey =
  | "country"
  | "department_id"
  | "job_role_id"
  | "level"
  | "employment_type"
  | "status"
  | "currency";

export type FilterOption = { value: string; label: string };

export type FilterDef = {
  key: FilterKey;
  /** "Country": the filter button says "Country: any", "Country: Germany". */
  label: string;
  options: FilterOption[];
};

/** The directory's list filters, with their options from GET /reference. */
export function filterDefs(reference: ReferenceData): FilterDef[] {
  return [
    {
      key: "country",
      label: "Country",
      options: reference.countries.map((c) => ({
        value: c.code,
        label: c.name,
      })),
    },
    {
      key: "department_id",
      label: "Department",
      options: reference.departments.map((d) => ({
        value: String(d.id),
        label: d.name,
      })),
    },
    {
      key: "job_role_id",
      label: "Job role",
      options: reference.job_roles.map((r) => ({
        value: String(r.id),
        label: r.title,
      })),
    },
    {
      key: "level",
      label: "Level",
      options: reference.levels.map((l) => ({
        value: l.code,
        label: `${l.code} ${l.label}`,
      })),
    },
    {
      key: "employment_type",
      label: "Employment type",
      options: reference.employment_types.map((t) => ({
        value: t,
        label: EMPLOYMENT_TYPE_LABELS[t],
      })),
    },
    {
      key: "status",
      label: "Status",
      options: EMPLOYEE_STATUSES.map((s) => ({
        value: s,
        label: STATUS_LABELS[s],
      })),
    },
    {
      key: "currency",
      label: "Currency",
      options: reference.currencies.map((c) => ({
        value: c.code,
        label: c.code,
      })),
    },
  ];
}

/** The chosen values of a filter, as strings. */
export function selectedValues(
  state: DirectoryState,
  key: FilterKey,
): string[] {
  return state[key].map(String);
}

/** True when the filter narrows the list (the default status, active, doesn't count). */
export function isActive(state: DirectoryState, key: FilterKey): boolean {
  return key === "status"
    ? !isDefaultStatus(state.status)
    : state[key].length > 0;
}

/** "any", the one choice, or "2 selected": what the filter button shows. */
export function summary(def: FilterDef, values: string[]): string {
  if (values.length === 0) return "any";
  if (values.length > 1) return `${values.length} selected`;
  return (
    def.options.find((o) => o.value === values[0])?.label ?? values[0] ?? ""
  );
}

export type DirectoryPatch = Partial<Nullable<DirectoryState>>;

/** The URL change that sets a filter to these values, back on page 1. */
export function filterPatch(key: FilterKey, values: string[]): DirectoryPatch {
  switch (key) {
    case "department_id":
      return { department_id: values.map(Number), page: null };
    case "job_role_id":
      return { job_role_id: values.map(Number), page: null };
    case "status":
      // None chosen means the API's default: active employees.
      return {
        status: values.length ? (values as DirectoryState["status"]) : null,
        page: null,
      };
    case "level":
      return { level: values as DirectoryState["level"], page: null };
    case "employment_type":
      return {
        employment_type: values as DirectoryState["employment_type"],
        page: null,
      };
    case "country":
      return { country: values, page: null };
    case "currency":
      return { currency: values, page: null };
  }
}
