"use client";

import { useId } from "react";

import {
  NativeSelect,
  NativeSelectOption,
} from "@/components/ui/native-select";

const SORTS = [
  { value: "", label: "Name, A to Z" }, // the API's default: last_name,first_name,id
  { value: "-last_name", label: "Name, Z to A" },
  { value: "employee_code", label: "Employee code" },
  { value: "-hire_date", label: "Newest hires first" },
  { value: "hire_date", label: "Longest serving first" },
  { value: "country", label: "Country" },
  { value: "-level", label: "Level, highest first" },
  { value: "level", label: "Level, lowest first" },
];

const PAY_SORTS = [
  { value: "-current_base", label: "Base pay, highest first" },
  { value: "current_base", label: "Base pay, lowest first" },
  { value: "-current_total", label: "Total pay, highest first" },
  { value: "current_total", label: "Total pay, lowest first" },
];

/**
 * "Sort by", one of the API's sort fields (docs/07-api-spec.md §6.1). The pay sorts are
 * offered only with SALARY_READ, and enabled only when the API can compare pay.
 */
export function SortSelect({
  value,
  onChange,
  showPay,
  payComparable,
  hint,
}: {
  value: string | null;
  onChange: (sort: string | null) => void;
  showPay: boolean;
  payComparable: boolean;
  hint: string;
}) {
  const id = useId();
  const options = showPay ? [...SORTS, ...PAY_SORTS] : SORTS;
  // A pay sort that no longer applies isn't sent, so the default is what the list shows.
  const stalePaySort =
    !payComparable && PAY_SORTS.some((o) => o.value === value);
  const current =
    value === "last_name" ||
    stalePaySort ||
    !options.some((o) => o.value === value)
      ? ""
      : (value ?? "");
  const showHint = showPay && !payComparable;
  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={id} className="text-sm font-bold text-ink-2">
        Sort by
      </label>
      <NativeSelect
        id={id}
        className="sm:w-64"
        value={current}
        onChange={(event) => onChange(event.target.value || null)}
        aria-describedby={showHint ? `${id}-hint` : undefined}
      >
        {SORTS.map((option) => (
          <NativeSelectOption key={option.value} value={option.value}>
            {option.label}
          </NativeSelectOption>
        ))}
        {showPay
          ? PAY_SORTS.map((option) => (
              <NativeSelectOption
                key={option.value}
                value={option.value}
                disabled={!payComparable}
              >
                {option.label}
              </NativeSelectOption>
            ))
          : null}
      </NativeSelect>
      {showHint ? (
        <p id={`${id}-hint`} className="max-w-[420px] text-sm text-ink-2">
          {hint}
        </p>
      ) : null}
    </div>
  );
}
