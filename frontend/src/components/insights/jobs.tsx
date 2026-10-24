import Link from "next/link";

import {
  EmptyState,
  ErrorState,
  MarginNote,
  Section,
} from "@/components/print";
import type { components } from "@/lib/api/schema";
import type { InsightsState } from "@/lib/insights-params";

import { Count, MoneyRange, PeriodMoney } from "./figures";
import { DirectionToggle, SplitByLevelToggle } from "./insights-controls";
import type { Result } from "./result";

type S = components["schemas"];

/** The section title: "What does each job pay in Germany?" once a country is chosen. */
export function jobsQuestion(countryName: string | null): string {
  return countryName
    ? `What does each job pay in ${countryName}?`
    : "What does each job pay?";
}

/** "Who earns the most in Germany?" or "the least". */
export function earnersQuestion(
  direction: InsightsState["direction"],
  countryName: string | null,
): string {
  const most = direction === "bottom" ? "the least" : "the most";
  return `Who earns ${most}${countryName ? ` in ${countryName}` : ""}?`;
}

const CHOOSE_COUNTRY = "Choose a country above";

/** "Pay by job title within a country": GET /insights/by-job-title (country required). */
export function JobTitlePay({
  result,
  countryName,
}: {
  result: Result<S["ByJobTitle"]> | null;
  countryName: string | null;
}) {
  const question = jobsQuestion(countryName);
  if (!result) {
    return (
      <Section question={question}>
        <EmptyState title={CHOOSE_COUNTRY}>
          Choose a country to compare jobs. Pay for a job only means something
          within one market and its currency.
        </EmptyState>
      </Section>
    );
  }
  if (!result.data) {
    return (
      <Section question={question}>
        <ErrorState {...result.problem} />
      </Section>
    );
  }
  const { groups } = result.data;
  return (
    <Section question={question}>
      <div className="mb-4">
        <SplitByLevelToggle />
      </div>
      {groups.length === 0 ? (
        <EmptyState title="No jobs match these filters" />
      ) : (
        <table className="w-full border-collapse text-[15px] tabular-nums">
          <thead>
            <tr className="text-left text-[13px] text-ink-2">
              <th scope="col" className="pr-3 pb-2.5 font-medium">
                Job
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
            {groups.map(({ job_role, level, stats }) => (
              <tr
                key={`${job_role.id}-${level ?? ""}`}
                className="border-t border-rule"
              >
                <th scope="row" className="py-3 pr-3 text-left font-medium">
                  {level ? `${job_role.title}, ${level}` : job_role.title}
                </th>
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
      )}
      <MarginNote className="mt-4">
        In {result.data.currency}, the currency these people are paid in.
      </MarginNote>
    </Section>
  );
}

/**
 * Top or bottom earners of one country (SALARY_READ only: these are individuals). Only
 * rendered for people who may see them; the API refuses everyone else anyway.
 */
export function TopEarners({
  result,
  direction,
  countryName,
}: {
  result: Result<S["TopEarners"]> | null;
  direction: InsightsState["direction"];
  countryName: string | null;
}) {
  const question = earnersQuestion(direction, countryName);
  const note = (
    <p className="text-sm text-ink-2">
      Visible to HR managers and admins only. Each view is recorded.
    </p>
  );
  if (!result) {
    return (
      <Section question={question}>
        <EmptyState title={CHOOSE_COUNTRY}>
          Earners are ranked within one country, in its own currency.
        </EmptyState>
        {note}
      </Section>
    );
  }
  return (
    <Section question={question}>
      <div className="mb-4 flex flex-wrap items-center gap-x-4 gap-y-2">
        <DirectionToggle />
        {note}
      </div>
      {!result.data ? (
        <ErrorState {...result.problem} />
      ) : result.data.items.length === 0 ? (
        <EmptyState title="Nobody matches these filters" />
      ) : (
        <ol className="flex flex-col">
          {result.data.items.map((earner) => (
            <li
              key={earner.employee_id}
              className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1 border-t border-rule py-2 text-[15px]"
            >
              <span className="min-w-0">
                <Link
                  href={`/employees/${earner.employee_id}`}
                  className="inline-flex min-h-11 items-center font-bold text-ink"
                >
                  {earner.first_name} {earner.last_name}
                </Link>{" "}
                <span className="text-ink-2">
                  {earner.job_role.title}, {earner.level} ·{" "}
                  {earner.department.name}
                </span>
              </span>
              <PeriodMoney
                amountMinor={earner.amount.amount_minor}
                currency={earner.amount.currency}
                className="font-serif text-lg font-semibold"
              />
            </li>
          ))}
        </ol>
      )}
    </Section>
  );
}
