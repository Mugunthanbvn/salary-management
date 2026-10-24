/**
 * The employee directory's state in the URL (docs/13-frontend-ux.md §3.2), shared by the
 * Server Component that calls GET /employees and the Client Components that change it.
 * Keys are the API's query parameter names; `period` is the one UI-only key.
 */
import {
  createLoader,
  createSerializer,
  parseAsInteger,
  parseAsNativeArrayOf,
  parseAsNumberLiteral,
  parseAsString,
  parseAsStringLiteral,
  type inferParserType,
  type Nullable,
} from "nuqs/server";

import type { components, paths } from "@/lib/api/schema";
import { EMPLOYEE_STATUSES, EMPLOYMENT_TYPES, LEVELS } from "@/lib/labels";

type ReferenceData = components["schemas"]["ReferenceData"];
export type ListQuery = NonNullable<
  paths["/api/v1/employees"]["get"]["parameters"]["query"]
>;

export const PAGE_SIZES = [25, 50, 100] as const;

export const directoryParsers = {
  q: parseAsString.withDefault(""),
  country: parseAsNativeArrayOf(parseAsString),
  department_id: parseAsNativeArrayOf(parseAsInteger),
  job_role_id: parseAsNativeArrayOf(parseAsInteger),
  level: parseAsNativeArrayOf(parseAsStringLiteral(LEVELS)),
  employment_type: parseAsNativeArrayOf(parseAsStringLiteral(EMPLOYMENT_TYPES)),
  // The API lists active employees when no status is given.
  status: parseAsNativeArrayOf(
    parseAsStringLiteral(EMPLOYEE_STATUSES),
  ).withDefault(["ACTIVE"]),
  currency: parseAsNativeArrayOf(parseAsString),
  salary_min: parseAsInteger,
  salary_max: parseAsInteger,
  salary_basis: parseAsStringLiteral(["local", "usd"] as const).withDefault(
    "local",
  ),
  comp: parseAsStringLiteral(["base", "total"] as const).withDefault("base"),
  sort: parseAsString,
  page: parseAsInteger.withDefault(1),
  page_size: parseAsNumberLiteral(PAGE_SIZES).withDefault(25),
  // UI only: amounts are annual; "monthly" shows annual ÷ 12 (lib/money.ts).
  period: parseAsStringLiteral(["annual", "monthly"] as const).withDefault(
    "annual",
  ),
};

export type DirectoryState = inferParserType<typeof directoryParsers>;

/** The state in a URL, a query string or the page's `searchParams` (also a Promise). */
export const loadDirectoryParams = createLoader(directoryParsers);

/** The query string ("?country=DE&page=2") for a state; defaults are left out. */
export const serializeDirectory = createSerializer(directoryParsers);

/** The URL keys "Clear filters" resets; sort, page size and the pay toggles stay. */
export const CLEARED_FILTERS = {
  q: null,
  country: null,
  department_id: null,
  job_role_id: null,
  level: null,
  employment_type: null,
  status: null,
  currency: null,
  salary_min: null,
  salary_max: null,
  salary_basis: null,
  page: null,
} as const;

/** True when anything narrows the list beyond the default (active employees). */
export function hasFilters(
  state: DirectoryState,
  options: { canReadSalaries: boolean; reference: ReferenceData },
): boolean {
  // Pay bounds count only when toListQuery sends them.
  const payBounds =
    options.canReadSalaries &&
    salaryCurrency(state, options.reference) !== null &&
    (state.salary_min !== null || state.salary_max !== null);
  return (
    payBounds ||
    state.q.trim() !== "" ||
    state.country.length > 0 ||
    state.department_id.length > 0 ||
    state.job_role_id.length > 0 ||
    state.level.length > 0 ||
    state.employment_type.length > 0 ||
    state.currency.length > 0 ||
    !isDefaultStatus(state.status)
  );
}

/** Just "ACTIVE": the list the API gives when no status is asked for. */
export function isDefaultStatus(status: DirectoryState["status"]): boolean {
  return status.length === 1 && status[0] === "ACTIVE";
}

export function withPayBoundsChecked(
  state: DirectoryState,
  patch: Partial<Nullable<DirectoryState>>,
  reference: ReferenceData,
): Partial<Nullable<DirectoryState>> {
  // Through the URL, so a null in the patch becomes that key's default.
  const next = loadDirectoryParams(serializeDirectory({ ...state, ...patch }));
  const bounded = state.salary_min !== null || state.salary_max !== null;
  if (
    !bounded ||
    salaryCurrency(next, reference) === salaryCurrency(state, reference)
  ) {
    return patch;
  }
  // The bounds are minor units of the old currency: €40,000 is not ¥4,000,000.
  return { ...patch, salary_min: null, salary_max: null };
}

/** Fields GET /employees can sort by (docs/07-api-spec.md §6.1). */
export const SORT_FIELDS = [
  "last_name",
  "first_name",
  "employee_code",
  "hire_date",
  "country",
  "level",
  "current_base",
  "current_total",
] as const;
export type SortField = (typeof SORT_FIELDS)[number];

/** These two need SALARY_READ, and one currency to compare in. */
export const SALARY_SORT_FIELDS: readonly SortField[] = [
  "current_base",
  "current_total",
];

const MIN_SEARCH_LENGTH = 2;
const MAX_SEARCH_LENGTH = 100;

/**
 * The currency pay is compared in, when the API can compare it: US dollars with
 * `salary_basis=usd`, else the one currency of the `currency` filter, else the currency of
 * the one country (every salary is in its country's currency). Null otherwise: the API
 * never compares raw amounts of two currencies, so it refuses a salary range or sort then.
 */
export function salaryCurrency(
  state: DirectoryState,
  reference: ReferenceData,
): string | null {
  if (state.salary_basis === "usd") return "USD";
  if (state.currency.length === 1) return state.currency[0] ?? null;
  if (state.country.length === 1) {
    const country = reference.countries.find(
      (c) => c.code === state.country[0],
    );
    return country?.default_currency ?? null;
  }
  return null;
}

/**
 * The GET /employees query for this state. Only what the API accepts from this person:
 * no salary range, basis, comp or salary sort without SALARY_READ (403), and no salary
 * range or sort while there is no one currency to compare in (422). `period` stays here.
 */
export function toListQuery(
  state: DirectoryState,
  {
    canReadSalaries,
    reference,
  }: { canReadSalaries: boolean; reference: ReferenceData },
): ListQuery {
  const query: ListQuery = {
    status: state.status,
    page: Math.max(1, state.page),
    page_size: state.page_size,
  };
  const q = state.q.trim();
  if (q.length >= MIN_SEARCH_LENGTH) query.q = q.slice(0, MAX_SEARCH_LENGTH);
  if (state.country.length) query.country = state.country;
  if (state.department_id.length) query.department_id = state.department_id;
  if (state.job_role_id.length) query.job_role_id = state.job_role_id;
  if (state.level.length) query.level = state.level;
  if (state.employment_type.length) {
    query.employment_type = state.employment_type;
  }
  if (state.currency.length) query.currency = state.currency;

  const comparable =
    canReadSalaries && salaryCurrency(state, reference) !== null;
  const sort = sortTokens(state.sort).filter(
    (token) => comparable || !SALARY_SORT_FIELDS.includes(fieldOf(token)),
  );
  if (sort.length) query.sort = sort.join(",");

  if (canReadSalaries && state.comp !== "base") query.comp = state.comp;
  if (comparable) {
    const min = bound(state.salary_min);
    const max = bound(state.salary_max);
    if (min !== null) query.salary_min = min;
    if (max !== null) query.salary_max = max;
    const salarySorted = sort.some((token) =>
      SALARY_SORT_FIELDS.includes(fieldOf(token)),
    );
    const ranged = min !== null || max !== null;
    if (state.salary_basis === "usd" && (ranged || salarySorted)) {
      query.salary_basis = "usd";
    }
  }
  return query;
}

/** The allowed tokens of a `sort` value ("-current_base,last_name"), in order. */
export function sortTokens(sort: string | null): string[] {
  return (sort ?? "")
    .split(",")
    .map((token) => token.trim())
    .filter((token) => isSortField(fieldOf(token)));
}

function fieldOf(token: string): SortField {
  return token.replace(/^-/, "") as SortField;
}

function isSortField(field: string): field is SortField {
  return (SORT_FIELDS as readonly string[]).includes(field);
}

function bound(value: number | null): number | null {
  return value !== null && value >= 0 ? value : null;
}
