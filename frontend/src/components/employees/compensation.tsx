"use client";

import { useQueryState } from "nuqs";

import { Highlight, Money } from "@/components/print";
import { SegmentedControl } from "@/components/ui/segmented-control";
import type { components } from "@/lib/api/schema";
import { formatDate } from "@/lib/dates";
import { directoryParsers } from "@/lib/directory-params";
import { COMPONENT_TYPE_LABELS, REASON_LABELS } from "@/lib/labels";
import { formatMoney } from "@/lib/money";

type EmployeeDetail = components["schemas"]["EmployeeDetail"];

/**
 * "What is Lena paid?": total pay highlighted, then base pay and each component, a year or
 * a month (`period` in the URL, display only). Every figure comes from the API; monthly is
 * annual ÷ 12 rounded half-even by lib/money.ts, for display.
 */
export function Compensation({ employee }: { employee: EmployeeDetail }) {
  const [period, setPeriod] = useQueryState(
    "period",
    directoryParsers.period.withOptions({ shallow: true, scroll: false }),
  );
  const {
    current_base: base,
    current_total: total,
    current_salary: salary,
  } = employee;
  if (!base || !total) return null;
  const monthly = period === "monthly";
  const other = monthly ? "annual" : "monthly";
  return (
    <div>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <p className="font-serif text-[34px] leading-[1.15] font-semibold sm:text-[44px]">
          <Highlight>
            <Money
              amountMinor={total.amount_minor}
              currency={total.currency}
              period={period}
            />
          </Highlight>{" "}
          <span className="text-[19px] font-normal text-ink-2 sm:text-[22px]">
            {monthly ? "a month" : "a year"} in total
          </span>
        </p>
        <SegmentedControl
          label="Period"
          options={[
            { value: "annual", label: "A year" },
            { value: "monthly", label: "A month" },
          ]}
          value={period}
          onChange={(next) => void setPeriod(next)}
        />
      </div>
      <p className="mt-2 mb-6 text-[15px] text-ink-2">
        That is{" "}
        {formatMoney(total.amount_minor, total.currency, { period: other })}{" "}
        {monthly ? "a year" : "a month"}.
        {salary ? (
          <>
            {" "}
            {REASON_LABELS[salary.reason]} on{" "}
            {formatDate(salary.effective_date)}.
          </>
        ) : null}
      </p>
      <dl className="grid max-w-[560px] grid-cols-[minmax(0,1fr)_auto] text-base">
        <dt className="border-t border-rule py-2.5">Base pay</dt>
        <dd className="border-t border-rule py-2.5 text-right font-bold">
          <Money
            amountMinor={base.amount_minor}
            currency={base.currency}
            period={period}
          />
        </dd>
        {salary?.components.map((component) => (
          <Row
            key={`${component.type}-${component.name}`}
            label={component.name}
            note={COMPONENT_TYPE_LABELS[component.type]}
          >
            <Money
              amountMinor={component.amount.amount_minor}
              currency={component.amount.currency}
              period={period}
            />
          </Row>
        ))}
      </dl>
    </div>
  );
}

function Row({
  label,
  note,
  children,
}: {
  label: string;
  note: string;
  children: React.ReactNode;
}) {
  return (
    <>
      <dt className="border-t border-rule py-2.5">
        {label}
        <span className="ml-2 text-sm text-ink-3">{note}</span>
      </dt>
      <dd className="border-t border-rule py-2.5 text-right">{children}</dd>
    </>
  );
}
