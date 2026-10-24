import Link from "next/link";

import { ErrorState, Highlight, MarginNote, Section } from "@/components/print";
import type { components } from "@/lib/api/schema";
import { formatDate } from "@/lib/dates";
import {
  serializeInsights,
  TOTAL_PAY_NOTE,
  type InsightsState,
} from "@/lib/insights-params";
import { EMPLOYMENT_TYPE_LABELS, STATUS_LABELS } from "@/lib/labels";
import { formatCount } from "@/lib/numbers";

import { Count, MoneyRange, PerPeriod, PeriodMoney } from "./figures";
import type { Result } from "./result";

type S = components["schemas"];
type ReferenceData = S["ReferenceData"];

export const COUNTRY_QUESTION =
  "What does a typical employee earn in each country?";

/** "Germany" for "DE"; the code itself if the reference data doesn't know it. */
export function countryName(code: string, reference: ReferenceData): string {
  return reference.countries.find((c) => c.code === code)?.name ?? code;
}

/** "full-time, active" or "full-time or part-time, active or terminated". */
function populationWords(state: InsightsState): string {
  const types = state.employment_type
    .map((type) => EMPLOYMENT_TYPE_LABELS[type].toLowerCase())
    .join(" or ");
  const statuses = state.status
    .map((status) => STATUS_LABELS[status].toLowerCase())
    .join(" or ");
  return `${types}, ${statuses}`;
}

/**
 * The page's summary sentence (DESIGN.md: a sentence, not KPI tiles): headcount, countries
 * and the total payroll in US$ with the exchange-rate date, all from GET /insights/overview.
 */
export function OverviewSentence({
  overview,
  state,
}: {
  overview: S["Overview"];
  state: InsightsState;
}) {
  if (overview.headcount === null || overview.total_payroll_usd === null) {
    return (
      <>Too few people match these filters to show their pay (fewer than 5).</>
    );
  }
  const countries = overview.by_country.length;
  const basis = state.comp === "total" ? "total pay" : "base pay";
  return (
    <>
      {formatCount(overview.headcount)} {populationWords(state)}{" "}
      {overview.headcount === 1 ? "employee" : "employees"} in{" "}
      {formatCount(countries)} {countries === 1 ? "country" : "countries"}, paid{" "}
      <Highlight>
        <PeriodMoney
          amountMinor={overview.total_payroll_usd.amount_minor}
          currency={overview.total_payroll_usd.currency}
          compact
          className="font-bold text-ink"
        />{" "}
        <PerPeriod />
      </Highlight>{" "}
      in {basis}
      {overview.fx_as_of
        ? `, at exchange rates of ${formatDate(overview.fx_as_of)}`
        : ""}
      .{state.comp === "total" ? ` ${TOTAL_PAY_NOTE}` : ""}
    </>
  );
}

/** "What does a typical employee earn in each country?": by_country of the overview. */
export function CountryPay({
  result,
  state,
  reference,
}: {
  result: Result<S["Overview"]>;
  state: InsightsState;
  reference: ReferenceData;
}) {
  if (!result.data) {
    return (
      <Section question={COUNTRY_QUESTION}>
        <ErrorState {...result.problem} />
      </Section>
    );
  }
  const rows = result.data.by_country;
  // Lowest and highest are one person's pay each: the API sends them only to HR.
  const showRange = rows.some((row) => row.local.min !== null);
  const fxAsOf = result.data.fx_as_of;
  const link = (code: string) =>
    `/insights${serializeInsights({ ...state, country: code })}`;

  return (
    <Section question={COUNTRY_QUESTION}>
      <table className="hidden w-full border-collapse text-[15px] tabular-nums sm:table">
        <thead>
          <tr className="text-left text-[13px] text-ink-2">
            <th scope="col" className="pr-3 pb-2.5 font-medium">
              Country
            </th>
            <th scope="col" className="px-3 pb-2.5 text-right font-medium">
              Median, local
            </th>
            <th scope="col" className="px-3 pb-2.5 text-right font-medium">
              Middle half earns
            </th>
            {showRange ? (
              <th
                scope="col"
                className="hidden px-3 pb-2.5 text-right font-medium lg:table-cell"
              >
                Lowest to highest
              </th>
            ) : null}
            <th scope="col" className="px-3 pb-2.5 text-right font-medium">
              Median in US$
            </th>
            <th scope="col" className="pb-2.5 pl-3 text-right font-medium">
              People
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.country_code} className="border-t border-rule">
              <th scope="row" className="py-2 pr-3 text-left font-medium">
                <Link
                  href={link(row.country_code)}
                  className="inline-flex min-h-11 items-center text-ink"
                >
                  {countryName(row.country_code, reference)}
                </Link>
              </th>
              <td className="px-3 py-2 text-right font-serif text-[19px] font-semibold">
                <PeriodMoney
                  amountMinor={row.local.median}
                  currency={row.local.currency}
                />
              </td>
              <td className="px-3 py-2 text-right text-ink-2">
                <MoneyRange
                  from={row.local.p25}
                  to={row.local.p75}
                  currency={row.local.currency}
                />
              </td>
              {showRange ? (
                <td className="hidden px-3 py-2 text-right text-ink-2 lg:table-cell">
                  <MoneyRange
                    from={row.local.min}
                    to={row.local.max}
                    currency={row.local.currency}
                  />
                </td>
              ) : null}
              <td className="px-3 py-2 text-right">
                <PeriodMoney
                  amountMinor={row.usd.median}
                  currency={row.usd.currency}
                />
              </td>
              <td className="py-2 pl-3 text-right text-ink-2">
                <Count value={row.local.count} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Phones: one row per country, no sideways scrolling. */}
      <ul className="sm:hidden">
        {rows.map((row) => (
          <li
            key={row.country_code}
            className="flex items-baseline justify-between gap-3 border-t border-rule py-3"
          >
            <span className="min-w-0">
              <Link href={link(row.country_code)} className="text-ink">
                {countryName(row.country_code, reference)}
              </Link>
              <span className="mt-0.5 block text-[13px] text-ink-3">
                <Count value={row.local.count} /> people
              </span>
            </span>
            <span className="text-right">
              <PeriodMoney
                amountMinor={row.local.median}
                currency={row.local.currency}
                className="font-serif text-[19px] font-semibold"
              />
              <span className="mt-0.5 block text-[13px] text-ink-3">
                <PeriodMoney
                  amountMinor={row.usd.median}
                  currency={row.usd.currency}
                />
              </span>
            </span>
          </li>
        ))}
      </ul>

      <MarginNote className="mt-4">
        Each country is shown in the currency people are paid in; the middle
        half earns between the 25th and 75th percentile.
        {fxAsOf
          ? ` US$ figures use one exchange rate per currency, set on ${formatDate(fxAsOf)} (illustrative).`
          : ""}
      </MarginNote>
    </Section>
  );
}
