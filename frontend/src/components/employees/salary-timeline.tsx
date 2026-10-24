import { MarginNote, Money } from "@/components/print";
import type { components } from "@/lib/api/schema";
import { formatDate } from "@/lib/dates";
import { REASON_LABELS } from "@/lib/labels";
import { formatChangePct } from "@/lib/numbers";

type SalaryHistoryRecord = components["schemas"]["SalaryHistoryRecord"];

/**
 * "How did Lena's pay get here?": every salary record, newest first, with the role and level
 * of that time, the base before and after, the change the API worked out, who made it and
 * the note. The API sends the records oldest first.
 */
export function SalaryTimeline({
  records,
}: {
  records: SalaryHistoryRecord[];
}) {
  const newestFirst = records
    .map((record, index) => ({ record, previous: records[index - 1] ?? null }))
    .reverse();
  return (
    <>
      <ol>
        {newestFirst.map(({ record, previous }) => (
          <li
            key={record.id}
            className="grid gap-x-6 gap-y-1 border-t border-rule py-3.5 text-[15px] sm:grid-cols-[130px_minmax(0,1fr)_auto] sm:items-baseline"
          >
            <span className="text-ink-2">
              {formatDate(record.effective_date)}
            </span>
            <span>
              <strong>{REASON_LABELS[record.reason]}</strong>{" "}
              <span className="text-ink-2">{detail(record, previous)}</span>
              {record.note ? (
                <span className="mt-1 block font-serif text-ink-2 italic">
                  {record.note}
                </span>
              ) : null}
            </span>
            <span className="sm:text-right">
              {previous ? (
                <span className="text-ink-2">
                  <Money
                    amountMinor={previous.base.amount_minor}
                    currency={previous.base.currency}
                  />{" "}
                  to{" "}
                </span>
              ) : null}
              <Money
                amountMinor={record.base.amount_minor}
                currency={record.base.currency}
                className="font-serif text-[18px] font-bold"
              />
              {record.base_change_pct !== null ? (
                <span className="text-ink-2">
                  {" "}
                  {formatChangePct(record.base_change_pct)}
                </span>
              ) : null}
            </span>
          </li>
        ))}
      </ol>
      <MarginNote className="mt-4">
        History is never edited. A mistake is fixed by adding a correction.
      </MarginNote>
    </>
  );
}

/** "as Software Engineer, L2", "L2 to L3, by Hema Iyer", "by Hema Iyer". */
function detail(
  record: SalaryHistoryRecord,
  previous: SalaryHistoryRecord | null,
): string {
  const parts: string[] = [];
  if (!previous) {
    parts.push(`as ${record.job_role.title}, ${record.level}`);
  } else {
    if (previous.job_role.id !== record.job_role.id) {
      parts.push(`${previous.job_role.title} to ${record.job_role.title}`);
    }
    if (previous.level !== record.level) {
      parts.push(`${previous.level} to ${record.level}`);
    }
  }
  const by = record.changed_by ? `by ${record.changed_by.full_name}` : "";
  return [parts.join(", "), by].filter(Boolean).join(", ");
}
