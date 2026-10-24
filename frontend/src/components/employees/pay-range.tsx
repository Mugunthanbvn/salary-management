"use client";

import { useId, useState, type FormEvent } from "react";

import { MarginNote } from "@/components/print";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { components } from "@/lib/api/schema";
import { salaryCurrency, type DirectoryState } from "@/lib/directory-params";
import { formatMoney } from "@/lib/money";
import { toMajorInput, toMinorUnits } from "@/lib/money-input";

import { exponentOf } from "./format";
import type { DirectoryPatch } from "./filters";

type ReferenceData = components["schemas"]["ReferenceData"];

export const PAY_NEEDS_ONE_CURRENCY =
  "To filter or sort by pay, choose one country or currency, or compare in US dollars.";

/** The pay currency and its exponent, when the API can compare pay; else null. */
export function payCurrency(
  state: DirectoryState,
  reference: ReferenceData,
): { code: string; exponent: number } | null {
  const code = salaryCurrency(state, reference);
  const exponent = code ? exponentOf(code, reference) : null;
  return code && exponent !== null ? { code, exponent } : null;
}

/** "Pay: any", "Pay: €40,000 to €60,000", "Pay: from €40,000": the button's text. */
export function paySummary(
  state: DirectoryState,
  reference: ReferenceData,
): string | null {
  const currency = payCurrency(state, reference);
  const { salary_min: min, salary_max: max } = state;
  if (!currency || (min === null && max === null)) return null;
  const money = (minor: number) => formatMoney(minor, currency.code);
  if (min !== null && max !== null) return `${money(min)} to ${money(max)}`;
  return min !== null ? `from ${money(min)}` : `up to ${money(max ?? 0)}`;
}

/**
 * The salary range (SALARY_READ only): yearly amounts typed in major units, sent in minor
 * units. The API compares pay in one currency or in US dollars, never across currencies,
 * so the fields wait for one country or currency, or for "US dollars".
 */
export function PayRange({
  state,
  reference,
  onChange,
}: {
  state: DirectoryState;
  reference: ReferenceData;
  onChange: (patch: DirectoryPatch) => void;
}) {
  const id = useId();
  const currency = payCurrency(state, reference);
  const initial = (minor: number | null) =>
    currency && minor !== null ? toMajorInput(minor, currency.exponent) : "";
  const [from, setFrom] = useState(() => initial(state.salary_min));
  const [to, setTo] = useState(() => initial(state.salary_max));
  const [errors, setErrors] = useState<{ from?: string; to?: string }>({});

  function apply(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!currency) return;
    const read = (text: string) =>
      text.trim() === ""
        ? ({ ok: true, minor: null } as const)
        : toMinorUnits(text, currency.code, currency.exponent);
    const min = read(from);
    const max = read(to);
    const next = {
      from: min.ok ? undefined : min.message,
      to: max.ok ? undefined : max.message,
    };
    if (min.ok && max.ok && min.minor !== null && max.minor !== null) {
      if (min.minor > max.minor)
        next.to = "Enter an amount above the first one";
    }
    setErrors(next);
    if (!min.ok || !max.ok || next.to) return;
    onChange({ salary_min: min.minor, salary_max: max.minor, page: null });
  }

  function compareIn(basis: "local" | "usd") {
    setFrom("");
    setTo("");
    setErrors({});
    // The amounts were in the other currency, so they go too.
    onChange({
      salary_basis: basis === "usd" ? "usd" : null,
      salary_min: null,
      salary_max: null,
      page: null,
    });
  }

  const unit = currency ? `${currency.code} a year` : "a year";
  const field = (
    name: "from" | "to",
    label: string,
    value: string,
    setValue: (value: string) => void,
  ) => {
    const inputId = `${id}-${name}`;
    const error = errors[name];
    return (
      <div className="flex min-w-0 flex-1 flex-col gap-2">
        <Label htmlFor={inputId}>
          {label} ({unit})
        </Label>
        <Input
          id={inputId}
          inputMode="decimal"
          autoComplete="off"
          value={value}
          disabled={!currency}
          onChange={(event) => setValue(event.target.value)}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? `${inputId}-error` : undefined}
        />
        {error ? (
          <p id={`${inputId}-error`} className="text-sm text-red-pen">
            {error}
          </p>
        ) : null}
      </div>
    );
  };

  return (
    <form onSubmit={apply} className="flex flex-col gap-4" noValidate>
      <fieldset>
        <legend className="mb-1 text-sm font-bold text-ink-2">
          Compare pay in
        </legend>
        {(
          [
            { value: "local", label: "Local currency" },
            { value: "usd", label: "US dollars" },
          ] as const
        ).map((option) => (
          <label
            key={option.value}
            className="flex min-h-11 cursor-pointer items-center gap-3 text-[15px]"
          >
            <input
              type="radio"
              name={`${id}-basis`}
              value={option.value}
              checked={state.salary_basis === option.value}
              onChange={() => compareIn(option.value)}
              className="size-5 accent-ink"
            />
            {option.label}
          </label>
        ))}
      </fieldset>
      <div className="flex flex-wrap gap-3">
        {field("from", "From", from, setFrom)}
        {field("to", "To", to, setTo)}
      </div>
      {currency ? (
        <MarginNote>
          {state.comp === "total" ? "Total pay" : "Base pay"} a year, as the
          list shows it.
        </MarginNote>
      ) : (
        <MarginNote>{PAY_NEEDS_ONE_CURRENCY}</MarginNote>
      )}
      <div className="flex gap-3">
        <Button type="submit" disabled={!currency}>
          Apply
        </Button>
        <Button
          type="button"
          variant="ghost"
          onClick={() => {
            setFrom("");
            setTo("");
            setErrors({});
            onChange({ salary_min: null, salary_max: null, page: null });
          }}
        >
          Clear pay
        </Button>
      </div>
    </form>
  );
}
