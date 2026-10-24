import { useId } from "react";

import {
  EmptyState,
  ErrorState,
  MarginNote,
  Section,
} from "@/components/print";
import type { components } from "@/lib/api/schema";
import { formatDate } from "@/lib/dates";
import { formatPercent } from "@/lib/numbers";
import { positionPercent } from "@/lib/position";

import { Count, Hidden, MoneyRange, PeriodMoney } from "./figures";
import type { Result } from "./result";

type S = components["schemas"];

export const DEPARTMENT_QUESTION = "How does pay differ between departments?";
export const COST_QUESTION = "Where does the payroll go?";

/** Says which currency a section is in: US$ when it mixes currencies, else local. */
function CurrencyNote({
  currency,
  fxAsOf,
  mixed,
}: {
  currency: string;
  fxAsOf: string | null;
  mixed: string;
}) {
  if (currency === "USD" && fxAsOf) {
    return (
      <MarginNote className="mt-4">
        In US$ at exchange rates of {formatDate(fxAsOf)} (illustrative), {mixed}
      </MarginNote>
    );
  }
  return (
    <MarginNote className="mt-4">
      In {currency}, the currency these people are paid in.
    </MarginNote>
  );
}

/** A thin ink bar: `percent` of its track, for display only. */
function Bar({ percent }: { percent: number }) {
  return (
    <span
      aria-hidden="true"
      className="block h-2.5 overflow-hidden rounded-[2px] bg-rule"
    >
      <span className="block h-full bg-ink" style={{ width: `${percent}%` }} />
    </span>
  );
}

/** "How does pay differ between departments?": GET /insights/by-department. */
export function DepartmentPay({
  result,
}: {
  result: Result<S["ByDepartment"]>;
}) {
  if (!result.data) {
    return (
      <Section question={DEPARTMENT_QUESTION}>
        <ErrorState {...result.problem} />
      </Section>
    );
  }
  const { groups, currency, fx_as_of } = result.data;
  if (groups.length === 0) {
    return (
      <Section question={DEPARTMENT_QUESTION}>
        <EmptyState title="No departments to compare" />
      </Section>
    );
  }
  // The bars only scale the API's medians to the widest one.
  const widest = Math.max(...groups.map((group) => group.stats.median ?? 0));

  return (
    <Section question={DEPARTMENT_QUESTION}>
      <table className="w-full border-collapse text-[15px] tabular-nums">
        <thead>
          <tr className="text-left text-[13px] text-ink-2">
            <th scope="col" className="pr-3 pb-2.5 font-medium">
              Department
            </th>
            <th
              scope="col"
              className="hidden w-[30%] px-3 pb-2.5 font-medium md:table-cell"
            >
              <span className="sr-only">Median as a bar</span>
            </th>
            <th scope="col" className="px-3 pb-2.5 text-right font-medium">
              Median
            </th>
            <th
              scope="col"
              className="hidden px-3 pb-2.5 text-right font-medium sm:table-cell"
            >
              Middle half earns
            </th>
            <th scope="col" className="pb-2.5 pl-3 text-right font-medium">
              People
            </th>
          </tr>
        </thead>
        <tbody>
          {groups.map(({ department, stats }) => (
            <tr key={department.id} className="border-t border-rule">
              <th scope="row" className="py-3 pr-3 text-left font-medium">
                {department.name}
              </th>
              <td className="hidden px-3 py-3 md:table-cell">
                {stats.median !== null ? (
                  <Bar percent={positionPercent(stats.median, 0, widest)} />
                ) : null}
              </td>
              <td className="px-3 py-3 text-right font-bold">
                <PeriodMoney
                  amountMinor={stats.median}
                  currency={stats.currency}
                />
              </td>
              <td className="hidden px-3 py-3 text-right text-ink-2 sm:table-cell">
                <MoneyRange
                  from={stats.p25}
                  to={stats.p75}
                  currency={stats.currency}
                />
              </td>
              <td className="py-3 pl-3 text-right text-ink-2">
                <Count value={stats.count} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <CurrencyNote
        currency={currency}
        fxAsOf={fx_as_of}
        mixed="because each department is paid in several currencies."
      />
    </Section>
  );
}

/** "Where does the payroll go?": GET /insights/department-cost, with each share. */
export function DepartmentCost({
  result,
}: {
  result: Result<S["DepartmentCosts"]>;
}) {
  if (!result.data) {
    return (
      <Section question={COST_QUESTION}>
        <ErrorState {...result.problem} />
      </Section>
    );
  }
  const { groups, currency, fx_as_of } = result.data;
  if (groups.length === 0) {
    return (
      <Section question={COST_QUESTION}>
        <EmptyState title="No payroll to show" />
      </Section>
    );
  }
  const widest = Math.max(
    ...groups.map((group) => Number(group.share_of_total ?? 0)),
  );

  return (
    <Section question={COST_QUESTION}>
      <ul className="flex flex-col">
        {groups.map((group) => (
          <CostRow key={group.department.id} group={group} widest={widest} />
        ))}
      </ul>
      <CurrencyNote
        currency={currency}
        fxAsOf={fx_as_of}
        mixed="so departments paid in different currencies add up."
      />
    </Section>
  );
}

function CostRow({
  group,
  widest,
}: {
  group: S["DepartmentCost"];
  widest: number;
}) {
  const nameId = useId();
  const cost = group.cost;
  return (
    <li
      aria-labelledby={nameId}
      className="grid grid-cols-[minmax(0,1fr)_auto_3.5rem] items-center gap-x-4 gap-y-1.5 border-t border-rule py-3 text-[15px] tabular-nums first:border-t-0 sm:grid-cols-[minmax(120px,200px)_minmax(0,1fr)_8rem_3.5rem]"
    >
      <span id={nameId} className="min-w-0 truncate">
        {group.department.name}
      </span>
      <span className="col-span-3 row-start-2 sm:col-span-1 sm:row-start-auto">
        {group.share_of_total !== null ? (
          <Bar
            percent={positionPercent(group.share_of_total, 0, widest || 1)}
          />
        ) : null}
      </span>
      <span className="text-right font-bold">
        {cost ? (
          <PeriodMoney
            amountMinor={cost.amount_minor}
            currency={cost.currency}
            compact
          />
        ) : (
          <Hidden />
        )}
        {cost && group.cost_usd && group.cost_usd.currency !== cost.currency ? (
          <span className="block text-[13px] font-normal text-ink-3">
            ≈{" "}
            <PeriodMoney
              amountMinor={group.cost_usd.amount_minor}
              currency={group.cost_usd.currency}
              compact
            />
          </span>
        ) : null}
      </span>
      <span className="text-right text-ink-2">
        {group.share_of_total !== null ? (
          formatPercent(group.share_of_total)
        ) : (
          <Hidden />
        )}
      </span>
    </li>
  );
}
