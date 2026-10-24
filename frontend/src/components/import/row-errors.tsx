import { cn } from "cn";

import type { components } from "@/lib/api/schema";

type ImportRowError = components["schemas"]["ImportRowError"];

type RowGroup = { row: number; errors: ImportRowError[] };

/** The errors of each spreadsheet row together, rows in order (the API sends them so). */
export function groupByRow(errors: ImportRowError[]): RowGroup[] {
  const groups = new Map<number, ImportRowError[]>();
  for (const error of errors) {
    const group = groups.get(error.row);
    if (group) group.push(error);
    else groups.set(error.row, [error]);
  }
  return [...groups]
    .sort(([a], [b]) => a - b)
    .map(([row, rowErrors]) => ({ row, errors: rowErrors }));
}

/** The refused cell as written, ringed in red pen like a mark on a printout. */
function MarkedValue({ value }: { value: string | null }) {
  return (
    <span
      className={cn(
        "inline-block max-w-full rounded-full border-2 border-red-pen px-2 py-0.5 break-words",
        value === null && "text-ink-3 italic",
      )}
    >
      {value ?? "(empty)"}
    </span>
  );
}

/**
 * Refused cells, grouped by spreadsheet row: a table from 640 px (row number once per group,
 * the bad value circled, the API's message as a margin note), a list of cards below it.
 */
export function RowErrors({
  errors,
  label = "Problems by row",
}: {
  errors: ImportRowError[];
  label?: string;
}) {
  const groups = groupByRow(errors);
  const th = "pb-2.5 text-left align-bottom text-[13px] font-normal text-ink-2";
  return (
    <>
      <div data-slot="row-errors-table" className="hidden sm:block">
        <table className="w-full border-collapse text-[15px]">
          <caption className="sr-only">{label}</caption>
          <thead>
            <tr className="border-b-2 border-ink">
              <th scope="col" className={cn(th, "w-20 pr-3")}>
                Row
              </th>
              <th scope="col" className={cn(th, "px-3")}>
                Column
              </th>
              <th scope="col" className={cn(th, "px-3")}>
                As written
              </th>
              <th scope="col" className={cn(th, "pl-3")}>
                What to fix
              </th>
            </tr>
          </thead>
          {groups.map(({ row, errors: rowErrors }) => (
            <tbody
              key={row}
              aria-label={`Row ${row}`}
              className="border-b border-rule"
            >
              {rowErrors.map((error, index) => (
                <tr key={`${error.column}-${index}`} className="align-top">
                  {index === 0 ? (
                    <th
                      scope="rowgroup"
                      rowSpan={rowErrors.length}
                      className="py-3 pr-3 text-left font-bold"
                    >
                      Row {row}
                    </th>
                  ) : null}
                  <td className="px-3 py-3 font-bold text-red-pen">
                    {error.column}
                  </td>
                  <td className="max-w-64 px-3 py-2.5">
                    <MarkedValue value={error.value} />
                  </td>
                  <td className="py-3 pl-3 font-serif text-[16px] leading-snug italic">
                    {error.message}
                  </td>
                </tr>
              ))}
            </tbody>
          ))}
        </table>
      </div>
      <ul
        data-slot="row-errors-cards"
        aria-label={label}
        className="border-t-2 border-ink sm:hidden"
      >
        {groups.map(({ row, errors: rowErrors }) => (
          <li key={row} className="border-b border-rule py-4">
            <h3 className="text-[15px] font-bold">Row {row}</h3>
            <dl className="mt-2 flex flex-col gap-3">
              {rowErrors.map((error, index) => (
                <div key={`${error.column}-${index}`}>
                  <dt className="flex flex-wrap items-center gap-2 text-[14px]">
                    <span className="font-bold text-red-pen">
                      {error.column}
                    </span>
                    <MarkedValue value={error.value} />
                  </dt>
                  <dd className="mt-1 font-serif text-[16px] leading-snug italic">
                    {error.message}
                  </dd>
                </div>
              ))}
            </dl>
          </li>
        ))}
      </ul>
    </>
  );
}
