"use client";

import { useId, useState } from "react";

import { Count, Hidden, MoneyRange } from "@/components/insights/figures";
import { Money, StatusWord } from "@/components/print";
import { useMe } from "@/components/shell/me-context";
import { Button } from "@/components/ui/button";
import type { components } from "@/lib/api/schema";
import { formatCount, formatRatio } from "@/lib/numbers";

import { BandStrip } from "./band-strip";
import { CohortSheet } from "./cohort-sheet";

type S = components["schemas"];
type Cohort = S["CohortEquity"];

const FIRST_ROWS = 12;

/** "Customer Success Manager, L2", as the printout writes a cohort. */
export function cohortName(cohort: Pick<Cohort, "job_role" | "level">) {
  return `${cohort.job_role.title}, ${cohort.level}`;
}

/** Most below band first, then most above; display order only (the API's counts). */
function byMostFlagged(cohorts: Cohort[]): Cohort[] {
  return [...cohorts].sort(
    (a, b) =>
      (b.underpaid_count ?? -1) - (a.underpaid_count ?? -1) ||
      (b.overpaid_count ?? -1) - (a.overpaid_count ?? -1),
  );
}

/**
 * The cohort view: each role and level of one country against its band, most flagged
 * first. With SALARY_READ a cohort opens to its people; a viewer sees counts and ratios.
 */
export function CohortList({
  cohorts,
  countryName,
}: {
  cohorts: Cohort[];
  countryName: string;
}) {
  const me = useMe();
  const canOpen = me.can("SALARY_READ");
  const [showAll, setShowAll] = useState(false);
  const [open, setOpen] = useState<Cohort | null>(null);
  const sorted = byMostFlagged(cohorts);
  const shown = showAll ? sorted : sorted.slice(0, FIRST_ROWS);

  return (
    <>
      <div
        aria-hidden="true"
        className="hidden grid-cols-[minmax(0,1.3fr)_minmax(0,1.4fr)_6rem_9rem] gap-x-4 pb-2 text-[13px] text-ink-2 lg:grid"
      >
        <span>Role and level</span>
        <span>Pay against the band</span>
        <span className="text-right">Compa-ratio</span>
        <span className="text-right">Below / above band</span>
      </div>
      <ul>
        {shown.map((cohort) => (
          <CohortRow
            key={`${cohort.job_role.id}-${cohort.level}`}
            cohort={cohort}
            onOpen={canOpen ? () => setOpen(cohort) : null}
          />
        ))}
      </ul>
      {sorted.length > FIRST_ROWS && !showAll ? (
        <Button
          variant="secondary"
          className="mt-4"
          onClick={() => setShowAll(true)}
        >
          Show all {formatCount(sorted.length)} roles and levels
        </Button>
      ) : null}
      {canOpen ? (
        <CohortSheet
          cohort={open}
          countryName={countryName}
          onClose={() => setOpen(null)}
        />
      ) : null}
    </>
  );
}

function Flags({ cohort }: { cohort: Cohort }) {
  const { underpaid_count: under, overpaid_count: over } = cohort;
  if (under === null || over === null) return <Hidden />;
  if (under === 0 && over === 0)
    return <StatusWord tone="plain">All in band</StatusWord>;
  return (
    <span className="flex flex-col items-end gap-0.5 max-lg:items-start">
      {under > 0 ? (
        <StatusWord tone="problem">{formatCount(under)} below band</StatusWord>
      ) : null}
      {over > 0 ? (
        <StatusWord tone="notice">{formatCount(over)} above band</StatusWord>
      ) : null}
    </span>
  );
}

function CohortRow({
  cohort,
  onOpen,
}: {
  cohort: Cohort;
  onOpen: (() => void) | null;
}) {
  const nameId = useId();
  const { stats, band } = cohort;
  const name = cohortName(cohort);
  return (
    <li
      aria-labelledby={nameId}
      className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-x-4 gap-y-2 border-t border-rule py-3 text-[15px] tabular-nums lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1.4fr)_6rem_9rem]"
    >
      <span className="col-start-1 row-start-1 min-w-0 lg:col-auto lg:row-auto">
        <span id={nameId} className="font-bold">
          {name}
        </span>
        <span className="block text-[13px] text-ink-3">
          {cohort.department.name} · <Count value={stats.count} /> people
        </span>
        {onOpen && stats.count ? (
          <Button
            variant="link"
            className="h-auto min-h-11 px-0"
            aria-label={`See the ${formatCount(stats.count)} people in ${name}`}
            onClick={onOpen}
          >
            See the {formatCount(stats.count)} people
          </Button>
        ) : null}
      </span>
      <span className="col-span-2 col-start-1 row-start-2 flex min-w-0 flex-col gap-1.5 lg:col-auto lg:row-auto">
        <BandStrip band={band} stats={stats} />
        <span className="flex flex-wrap justify-between gap-x-4 text-[13px] text-ink-2">
          <span>
            Band <Money amountMinor={band.min} currency={band.currency} /> to{" "}
            <Money amountMinor={band.max} currency={band.currency} />
          </span>
          <span>
            Median{" "}
            {stats.median !== null ? (
              <Money
                amountMinor={stats.median}
                currency={stats.currency}
                className="font-bold text-ink"
              />
            ) : (
              <Hidden />
            )}
          </span>
          <span className="sr-only">
            Middle half earns{" "}
            <MoneyRange
              from={stats.p25}
              to={stats.p75}
              currency={stats.currency}
            />
          </span>
        </span>
      </span>
      <span className="col-start-2 row-start-1 text-right font-bold lg:col-auto lg:row-auto">
        <span className="sr-only">Median compa-ratio </span>
        {cohort.median_compa_ratio !== null ? (
          formatRatio(cohort.median_compa_ratio)
        ) : (
          <Hidden />
        )}
      </span>
      <span className="col-span-2 col-start-1 row-start-3 text-sm lg:col-auto lg:row-auto lg:text-right">
        <Flags cohort={cohort} />
      </span>
    </li>
  );
}
