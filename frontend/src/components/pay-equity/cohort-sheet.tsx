"use client";

import Link from "next/link";
import { useEffect, useId, useState } from "react";

import { ErrorState, Money, StatusWord } from "@/components/print";
import type { PlainProblem } from "@/components/insights/result";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api/client";
import { toProblem } from "@/lib/api/problem";
import type { components } from "@/lib/api/schema";
import { formatRatio } from "@/lib/numbers";

type S = components["schemas"];
type Cohort = S["CohortEquity"];
type Member = S["CohortMember"];

type Loaded =
  | { data: S["CohortMembers"]; problem: null }
  | { data: null; problem: PlainProblem };

/**
 * The drill-down (SALARY_READ only): every member of one cohort with their base pay,
 * compa-ratio and flag, from GET /insights/pay-equity/cohort (audited by the API). A side
 * sheet on desktop, full screen on phones.
 */
export function CohortSheet({
  cohort,
  countryName,
  onClose,
}: {
  cohort: Cohort | null;
  countryName: string;
  onClose: () => void;
}) {
  return (
    <Sheet open={cohort !== null} onOpenChange={(open) => !open && onClose()}>
      <SheetContent side="right" className="sm:max-w-lg">
        {cohort ? (
          <Members
            key={`${cohort.job_role.id}-${cohort.level}-${cohort.country_code}`}
            cohort={cohort}
            countryName={countryName}
          />
        ) : null}
      </SheetContent>
    </Sheet>
  );
}

/** GET /insights/pay-equity/cohort for one cohort, as data or a plain problem. */
async function fetchMembers(cohort: Cohort): Promise<Loaded> {
  const { data, error, response } = await api.GET(
    "/api/v1/insights/pay-equity/cohort",
    {
      params: {
        query: {
          job_role_id: cohort.job_role.id,
          level: cohort.level,
          country: cohort.country_code,
        },
      },
    },
  );
  if (data) return { data, problem: null };
  const problem = await toProblem(response, error);
  return {
    data: null,
    problem: {
      title: problem.title,
      detail: problem.detail,
      requestId: problem.requestId,
    },
  };
}

function Members({
  cohort,
  countryName,
}: {
  cohort: Cohort;
  countryName: string;
}) {
  const [loaded, setLoaded] = useState<Loaded | null>(null);

  useEffect(() => {
    let live = true;
    void fetchMembers(cohort).then((result) => {
      if (live) setLoaded(result);
    });
    return () => {
      live = false;
    };
  }, [cohort]);

  const retry = () => {
    setLoaded(null);
    void fetchMembers(cohort).then(setLoaded);
  };

  const band = cohort.band;
  return (
    <>
      <SheetHeader>
        <SheetTitle>
          {cohort.job_role.title}, {cohort.level} in {countryName}
        </SheetTitle>
        <SheetDescription>
          Band <Money amountMinor={band.min} currency={band.currency} /> to{" "}
          <Money amountMinor={band.max} currency={band.currency} />, middle{" "}
          <Money amountMinor={band.mid} currency={band.currency} />. Base pay a
          year.
        </SheetDescription>
      </SheetHeader>
      <div className="px-4 pb-6">
        {loaded === null ? (
          <div aria-busy="true" className="flex flex-col gap-3 pt-4">
            <p className="sr-only" role="status">
              Loading…
            </p>
            {[0, 1, 2, 3].map((row) => (
              <Skeleton key={row} className="h-11 w-full" />
            ))}
          </div>
        ) : loaded.data ? (
          <ul>
            {loaded.data.members.map((member) => (
              <MemberRow key={member.employee_id} member={member} />
            ))}
          </ul>
        ) : (
          <ErrorState {...loaded.problem} onRetry={retry} />
        )}
        <p className="mt-4 text-sm text-ink-2">
          Names and pay are visible to HR managers and admins only. Each view is
          recorded.
        </p>
      </div>
    </>
  );
}

const FLAG_WORDS = {
  UNDERPAID: { tone: "problem", text: "Below band" },
  OVERPAID: { tone: "notice", text: "Above band" },
  IN_BAND: { tone: "plain", text: "In band" },
} as const;

const NO_RATIO_WORDS = {
  not_full_time: "Not full-time",
  no_band: "No band",
} as const;

function MemberRow({ member }: { member: Member }) {
  const nameId = useId();
  const flag = member.flag ? FLAG_WORDS[member.flag] : null;
  return (
    <li
      aria-labelledby={nameId}
      className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1 border-t border-rule py-2 text-[15px] tabular-nums first:border-t-0"
    >
      <span className="min-w-0">
        <Link
          id={nameId}
          href={`/employees/${member.employee_id}`}
          className="inline-flex min-h-11 items-center font-bold text-ink"
        >
          {member.first_name} {member.last_name}
        </Link>{" "}
        <span className="text-ink-3">{member.employee_code}</span>
      </span>
      <span className="flex items-baseline gap-4">
        <Money
          amountMinor={member.base.amount_minor}
          currency={member.base.currency}
          className="font-bold"
        />
        <span className="w-10 text-right">
          {member.compa_ratio !== null ? formatRatio(member.compa_ratio) : "—"}
        </span>
        <span className="w-24 text-right text-sm">
          {flag ? (
            <StatusWord tone={flag.tone}>{flag.text}</StatusWord>
          ) : member.no_compa_ratio_reason ? (
            NO_RATIO_WORDS[member.no_compa_ratio_reason]
          ) : null}
        </span>
      </span>
    </li>
  );
}
