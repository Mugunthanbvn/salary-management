"use client";

import { cn } from "cn";
import { useQueryState } from "nuqs";

import { Money } from "@/components/print";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { insightsParsers } from "@/lib/insights-params";

/** Why a figure is a dash (docs/13-frontend-ux.md §3.5). */
export const HIDDEN_REASON =
  "Hidden to protect individual pay (fewer than 5 people)";

/**
 * A figure the API hid (`suppressed`, or `null` for this person): a dash whose reason opens
 * on tap or click as well as on hover, so phones can read it too.
 */
export function Hidden({ className }: { className?: string }) {
  return (
    <Popover>
      <PopoverTrigger
        aria-label={HIDDEN_REASON}
        title={HIDDEN_REASON}
        className={cn(
          "inline-flex min-h-11 min-w-11 cursor-help items-center justify-center text-ink-2 underline decoration-dotted underline-offset-4",
          className,
        )}
      >
        —
      </PopoverTrigger>
      <PopoverContent className="w-64 text-sm" align="end">
        {HIDDEN_REASON}
      </PopoverContent>
    </Popover>
  );
}

/** The Annual / Monthly toggle's value: display only, so changing it fetches nothing. */
export function usePeriod() {
  const [period] = useQueryState("period", insightsParsers.period);
  return period;
}

/** An annual amount from the API, shown a year or a month at a time as the URL says. */
export function PeriodMoney({
  amountMinor,
  currency,
  compact,
  className,
}: {
  amountMinor: number | null;
  currency: string;
  compact?: boolean;
  className?: string;
}) {
  const period = usePeriod();
  if (amountMinor === null) return <Hidden />;
  return (
    <Money
      amountMinor={amountMinor}
      currency={currency}
      period={period}
      compact={compact}
      className={className}
    />
  );
}
