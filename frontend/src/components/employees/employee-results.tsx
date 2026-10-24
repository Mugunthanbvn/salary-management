"use client";

import { cn } from "cn";
import Link from "next/link";

import { EmptyState, Money } from "@/components/print";
import { useMe } from "@/components/shell/me-context";
import { Button } from "@/components/ui/button";
import {
  NativeSelect,
  NativeSelectOption,
} from "@/components/ui/native-select";
import type { components } from "@/lib/api/schema";
import {
  PAGE_SIZES,
  serializeDirectory,
  sortTokens,
  type DirectoryState,
  CLEARED_FILTERS,
  hasFilters,
} from "@/lib/directory-params";
import { formatDate } from "@/lib/dates";
import { EMPLOYMENT_TYPE_LABELS } from "@/lib/labels";
import { formatCount } from "@/lib/numbers";

import { useDirectoryPending, useDirectoryState } from "./directory-state";
import { countryName, fullName, roleAndLevel } from "./format";

type EmployeePage = components["schemas"]["EmployeePage"];
type EmployeeListItem = components["schemas"]["EmployeeListItem"];
type ReferenceData = components["schemas"]["ReferenceData"];

/**
 * One page of GET /employees: a table from 640 px, a list of cards below it (no sideways
 * scrolling on phones), and the paging. The pay column appears only with SALARY_READ;
 * for anyone else the API sends no salary at all, and there is no column to fill.
 */
export function EmployeeResults({
  page,
  reference,
}: {
  page: EmployeePage;
  reference: ReferenceData;
}) {
  const me = useMe();
  const [state, setState] = useDirectoryState();
  const pending = useDirectoryPending();
  const showPay = me.can("SALARY_READ");

  if (page.items.length === 0) {
    return (
      <NoResults
        page={page}
        state={state}
        onClear={() => void setState(CLEARED_FILTERS)}
      />
    );
  }

  return (
    <div
      aria-busy={pending || undefined}
      className={cn("mt-6 transition-opacity", pending && "opacity-60")}
    >
      <ResultsTable
        items={page.items}
        reference={reference}
        state={state}
        showPay={showPay}
      />
      <ResultCards
        items={page.items}
        reference={reference}
        state={state}
        showPay={showPay}
      />
      <Paging
        page={page}
        state={state}
        onPageSize={(size) => void setState({ page_size: size, page: null })}
      />
    </div>
  );
}

type ListProps = {
  items: EmployeeListItem[];
  reference: ReferenceData;
  state: DirectoryState;
  showPay: boolean;
};

function payHeading(state: DirectoryState): string {
  const amount = state.comp === "total" ? "Total pay" : "Base pay";
  return `${amount} ${state.period === "monthly" ? "a month" : "a year"}`;
}

function PayAmount({
  employee,
  state,
  className,
}: {
  employee: EmployeeListItem;
  state: DirectoryState;
  className?: string;
}) {
  const amount =
    state.comp === "total" ? employee.current_total : employee.current_base;
  if (!amount) return null;
  return (
    <Money
      amountMinor={amount.amount_minor}
      currency={amount.currency}
      period={state.period}
      className={className}
    />
  );
}

/** Which column the list is sorted by, for `aria-sort`. */
type Column = "name" | "role" | "country" | "pay" | "hired";

function sortedColumn(
  state: DirectoryState,
): { column: Column; descending: boolean } | null {
  const [first] = sortTokens(state.sort);
  if (!first) return { column: "name", descending: false };
  const descending = first.startsWith("-");
  const field = first.replace(/^-/, "");
  const columns: Record<string, Column> = {
    last_name: "name",
    first_name: "name",
    level: "role",
    country: "country",
    current_base: "pay",
    current_total: "pay",
    hire_date: "hired",
  };
  const column = columns[field];
  return column ? { column, descending } : null;
}

function ResultsTable({ items, reference, state, showPay }: ListProps) {
  const sorted = sortedColumn(state);
  const ariaSort = (column: Column) =>
    sorted?.column === column
      ? sorted.descending
        ? ("descending" as const)
        : ("ascending" as const)
      : undefined;
  const th = "pb-2.5 text-left align-bottom text-[13px] font-normal text-ink-2";
  return (
    <div data-slot="results-table" className="hidden overflow-x-auto sm:block">
      <table className="w-full border-collapse text-[15px]">
        <caption className="sr-only">Employees</caption>
        <thead>
          <tr className="border-b-2 border-ink">
            <th
              scope="col"
              aria-sort={ariaSort("name")}
              className={cn(th, "pr-3")}
            >
              Name
            </th>
            <th
              scope="col"
              aria-sort={ariaSort("role")}
              className={cn(th, "px-3")}
            >
              Job role and level
            </th>
            <th scope="col" className={cn(th, "hidden px-3 md:table-cell")}>
              Department
            </th>
            <th
              scope="col"
              aria-sort={ariaSort("country")}
              className={cn(th, "px-3")}
            >
              Country
            </th>
            <th scope="col" className={cn(th, "hidden px-3 lg:table-cell")}>
              Type
            </th>
            {showPay ? (
              <th
                scope="col"
                aria-sort={ariaSort("pay")}
                className={cn(th, "px-3 text-right")}
              >
                {payHeading(state)}
              </th>
            ) : null}
            <th
              scope="col"
              aria-sort={ariaSort("hired")}
              className={cn(th, "hidden pl-3 lg:table-cell")}
            >
              Hired
            </th>
          </tr>
        </thead>
        <tbody>
          {items.map((employee) => {
            const terminated = employee.status === "TERMINATED";
            return (
              <tr
                key={employee.id}
                className={cn(
                  "border-b border-rule align-top",
                  terminated && "text-ink-3",
                )}
              >
                <th scope="row" className="py-3.5 pr-3 text-left font-normal">
                  <Link
                    href={`/employees/${employee.id}`}
                    className={cn(
                      // Ink names as on the printout; the underline shows the link.
                      "inline-flex min-h-6 items-center font-bold text-ink no-underline hover:text-ink hover:underline hover:underline-offset-4",
                      terminated && "text-ink-3 hover:text-ink-3",
                    )}
                  >
                    {fullName(employee)}
                  </Link>
                  <span className="mt-0.5 block text-[13px] text-ink-3">
                    {employee.employee_code}
                    {terminated ? (
                      <>
                        {" · "}
                        <span className="font-bold text-ink-2">Terminated</span>
                      </>
                    ) : null}
                  </span>
                </th>
                <td className="px-3 py-3.5">{roleAndLevel(employee)}</td>
                <td className="hidden px-3 py-3.5 md:table-cell">
                  {employee.department.name}
                </td>
                <td className="px-3 py-3.5">
                  {countryName(employee.country_code, reference)}
                </td>
                <td className="hidden px-3 py-3.5 lg:table-cell">
                  {EMPLOYMENT_TYPE_LABELS[employee.employment_type]}
                </td>
                {showPay ? (
                  <td className="px-3 py-3 text-right font-serif text-[18px] font-semibold">
                    <PayAmount employee={employee} state={state} />
                  </td>
                ) : null}
                <td className="hidden py-3.5 pl-3 whitespace-nowrap text-ink-3 lg:table-cell">
                  {formatDate(employee.hire_date)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function ResultCards({ items, reference, state, showPay }: ListProps) {
  return (
    <ul aria-label="Employees" className="border-b border-rule sm:hidden">
      {items.map((employee) => {
        const terminated = employee.status === "TERMINATED";
        return (
          <li key={employee.id} className="border-t border-rule">
            <Link
              href={`/employees/${employee.id}`}
              className={cn(
                "flex min-h-11 justify-between gap-3 py-3.5 no-underline",
                terminated ? "text-ink-3" : "text-ink hover:text-ink",
              )}
            >
              <span className="min-w-0">
                <span className="block truncate text-base font-bold">
                  {fullName(employee)}
                </span>
                <span className="mt-0.5 block text-[13px] text-ink-3">
                  {roleAndLevel(employee)}
                </span>
                <span className="mt-0.5 block text-[13px] text-ink-3">
                  {countryName(employee.country_code, reference)},{" "}
                  {employee.employee_code}
                </span>
              </span>
              <span className="shrink-0 text-right">
                {showPay ? (
                  <PayAmount
                    employee={employee}
                    state={state}
                    className="block font-serif text-[18px] font-semibold"
                  />
                ) : null}
                {terminated ? (
                  <span className="mt-1 block text-[13px] font-bold text-ink-2">
                    Terminated
                  </span>
                ) : null}
              </span>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}

function pageHref(state: DirectoryState, page: number): string {
  return `/employees${serializeDirectory({ ...state, page: page === 1 ? null : page })}`;
}

function Paging({
  page,
  state,
  onPageSize,
}: {
  page: EmployeePage;
  state: DirectoryState;
  onPageSize: (size: (typeof PAGE_SIZES)[number]) => void;
}) {
  const first = (page.page - 1) * page.page_size + 1;
  const last = Math.min(page.page * page.page_size, page.total);
  const hasPrevious = page.page > 1;
  const hasNext = last < page.total;
  const pageLink =
    "inline-flex min-h-11 items-center rounded-control border border-ink px-4 text-ink no-underline hover:bg-rule hover:text-ink";
  return (
    <nav
      aria-label="Pages"
      className="mt-6 flex flex-wrap items-center justify-between gap-3 text-[15px]"
    >
      <p className="text-ink-2">
        <span className="hidden sm:inline">Showing </span>
        {formatCount(first)}–{formatCount(last)} of {formatCount(page.total)}
      </p>
      <div className="flex flex-wrap items-center gap-3">
        <div
          data-slot="page-size"
          className="hidden items-center gap-2 sm:flex"
        >
          <label htmlFor="page-size" className="text-sm text-ink-2">
            Rows per page
          </label>
          <NativeSelect
            id="page-size"
            className="w-24"
            value={String(state.page_size)}
            onChange={(event) =>
              onPageSize(
                Number(event.target.value) as (typeof PAGE_SIZES)[number],
              )
            }
          >
            {PAGE_SIZES.map((size) => (
              <NativeSelectOption key={size} value={size}>
                {size}
              </NativeSelectOption>
            ))}
          </NativeSelect>
        </div>
        {hasPrevious ? (
          <Link href={pageHref(state, page.page - 1)} className={pageLink}>
            Previous
          </Link>
        ) : null}
        {hasNext ? (
          <Link href={pageHref(state, page.page + 1)} className={pageLink}>
            Next
          </Link>
        ) : null}
      </div>
    </nav>
  );
}

function NoResults({
  page,
  state,
  onClear,
}: {
  page: EmployeePage;
  state: DirectoryState;
  onClear: () => void;
}) {
  if (page.total > 0) {
    return (
      <EmptyState
        title="This page is past the end of the list"
        action={
          <Link
            href={pageHref(state, 1)}
            className="inline-flex min-h-11 items-center font-bold"
          >
            Go to the first page
          </Link>
        }
      >
        The list has {formatCount(page.total)}{" "}
        {page.total === 1 ? "employee" : "employees"}.
      </EmptyState>
    );
  }
  if (hasFilters(state)) {
    return (
      <EmptyState
        title="No employees match these filters"
        action={
          <Button variant="secondary" onClick={onClear}>
            Clear filters
          </Button>
        }
      >
        Try fewer filters, or check the spelling of the name.
      </EmptyState>
    );
  }
  return (
    <EmptyState title="No employees yet">
      Employees appear here once they are added or imported.
    </EmptyState>
  );
}
