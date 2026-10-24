import type { ReactNode } from "react";
import { cn } from "cn";

import { formatMoney, type FormatMoneyOptions } from "@/lib/money";

/** The highlighter mark: the one key figure or phrase of a section, at most once. */
export function Highlight({ children }: { children: ReactNode }) {
  return <mark className="bg-transparent highlight">{children}</mark>;
}

/** A red-pen underline for a problem ("8% below its pay bands"). */
export function RedPen({ children }: { children: ReactNode }) {
  return <span className="red-pen">{children}</span>;
}

/** A short italic serif note in the margin that explains a number or a rule. */
export function MarginNote({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <p
      className={cn(
        "font-serif text-[15px] leading-normal text-ink-2 italic",
        className,
      )}
    >
      {children}
    </p>
  );
}

const STATUS_TONES = {
  /** Below band, errors: red-pen underline. */
  problem:
    "font-bold text-red-pen underline decoration-red-pen decoration-2 underline-offset-[3px]",
  /** Above band: blue-pen. */
  notice: "text-blue-pen",
  /** In band, nothing to act on. */
  plain: "text-ink-2",
} as const;

/** A status as a word, never a pill or a colour alone: "Below band", "In band". */
export function StatusWord({
  tone,
  children,
}: {
  tone: keyof typeof STATUS_TONES;
  children: ReactNode;
}) {
  return <span className={STATUS_TONES[tone]}>{children}</span>;
}

type MoneyProps = FormatMoneyOptions & {
  /** `amount_minor` from the API's money object. */
  amountMinor: number | bigint | string;
  currency: string;
  className?: string;
};

/** An amount with its currency, formatted by lib/money.ts; it never wraps. */
export function Money({
  amountMinor,
  currency,
  className,
  ...options
}: MoneyProps) {
  return (
    <span className={cn("whitespace-nowrap tabular-nums", className)}>
      {formatMoney(amountMinor, currency, options)}
    </span>
  );
}
