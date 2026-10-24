import { cn } from "cn";

import { Money } from "@/components/print";
import type { components } from "@/lib/api/schema";
import { formatDate } from "@/lib/dates";

import { fullName } from "../employees/format";

type ImportPreviewRow = components["schemas"]["ImportPreviewRow"];

const LABEL = "Who will be added";

/**
 * The valid rows as they will be imported (the API sends the first 50): a table from 640 px,
 * cards below it. Pay is annual, in the row's currency, formatted by lib/money.ts.
 */
export function PreviewRows({ rows }: { rows: ImportPreviewRow[] }) {
  const th = "pb-2.5 text-left align-bottom text-[13px] font-normal text-ink-2";
  return (
    <>
      <div data-slot="preview-table" className="hidden sm:block">
        <table className="w-full border-collapse text-[15px]">
          <caption className="sr-only">{LABEL}</caption>
          <thead>
            <tr className="border-b-2 border-ink">
              <th scope="col" className={cn(th, "pr-3")}>
                Row
              </th>
              <th scope="col" className={cn(th, "px-3")}>
                Name
              </th>
              <th scope="col" className={cn(th, "px-3")}>
                Job role and level
              </th>
              <th scope="col" className={cn(th, "hidden px-3 lg:table-cell")}>
                Department
              </th>
              <th scope="col" className={cn(th, "px-3")}>
                Country
              </th>
              <th scope="col" className={cn(th, "hidden px-3 lg:table-cell")}>
                Hired
              </th>
              <th scope="col" className={cn(th, "px-3 text-right")}>
                Base pay a year
              </th>
              <th scope="col" className={cn(th, "pl-3 text-right")}>
                Total pay a year
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.row} className="border-b border-rule align-top">
                <td className="py-3 pr-3 text-ink-3">{row.row}</td>
                <th scope="row" className="px-3 py-3 text-left font-normal">
                  <span className="font-bold">{fullName(row)}</span>
                  <span className="mt-0.5 block text-[13px] whitespace-nowrap text-ink-3">
                    {row.employee_code}
                  </span>
                </th>
                <td className="px-3 py-3">
                  {row.job_role}, {row.level}
                </td>
                <td className="hidden px-3 py-3 lg:table-cell">
                  {row.department}
                </td>
                <td className="px-3 py-3">{row.country_code}</td>
                <td className="hidden px-3 py-3 whitespace-nowrap text-ink-3 lg:table-cell">
                  {formatDate(row.hire_date)}
                </td>
                <td className="px-3 py-3 text-right">
                  <Money
                    amountMinor={row.base.amount_minor}
                    currency={row.base.currency}
                  />
                </td>
                <td className="py-3 pl-3 text-right font-bold">
                  <Money
                    amountMinor={row.total.amount_minor}
                    currency={row.total.currency}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <ul
        data-slot="preview-cards"
        aria-label={LABEL}
        className="border-t-2 border-ink sm:hidden"
      >
        {rows.map((row) => (
          <li key={row.row} className="border-b border-rule py-3.5">
            <div className="flex items-baseline justify-between gap-3">
              <span className="min-w-0 font-bold">{fullName(row)}</span>
              <Money
                amountMinor={row.total.amount_minor}
                currency={row.total.currency}
                className="font-bold"
              />
            </div>
            <p className="mt-0.5 text-[14px] text-ink-2">
              {row.job_role}, {row.level} · {row.country_code}
            </p>
            <p className="mt-0.5 text-[13px] text-ink-3">
              Row {row.row} ·{" "}
              <span className="whitespace-nowrap">{row.employee_code}</span> ·
              base{" "}
              <Money
                amountMinor={row.base.amount_minor}
                currency={row.base.currency}
              />{" "}
              a year
            </p>
          </li>
        ))}
      </ul>
    </>
  );
}
