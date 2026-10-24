/**
 * Display formatting for the non-money numbers the API sends. Ratios arrive as decimal
 * strings (`"0.9234"`) and are formatted from that exact string, never through a float,
 * rounding half-even like the API. The locale is fixed, so server and browser agree.
 */
import { numberFormat } from "./intl";

const RATIO = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
  roundingMode: "halfEven",
  signDisplay: "negative", // "-0.001" shows "0.00", not "-0.00"
});

/** A ratio such as the compa-ratio: `"0.9234"` → `"0.92"`. */
export function formatRatio(ratio: string): string {
  return RATIO.format(ratio as Intl.StringNumericLiteral);
}

/** A share or gap as a percentage: `"0.4412"` → `"44%"`; `fractionDigits` defaults to 0. */
export function formatPercent(
  ratio: string,
  { fractionDigits = 0 }: { fractionDigits?: number } = {},
): string {
  return numberFormat("en-US", {
    style: "percent",
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
    roundingMode: "halfEven",
    signDisplay: "negative", // "-0.001" shows "0%", not "-0%"
  }).format(ratio as Intl.StringNumericLiteral);
}

const CHANGE_PCT = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
  roundingMode: "halfEven",
  signDisplay: "exceptZero", // "+12.5%", "-3.2%", and "0.0%" for no change
});

/**
 * A change already in percent, as the salary history sends it (`base_change_pct: "12.50"`):
 * `"12.50"` → `"+12.5%"`. One decimal, like the printout.
 */
export function formatChangePct(pct: string): string {
  return `${CHANGE_PCT.format(pct as Intl.StringNumericLiteral)}%`;
}

const COUNT = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });

/** A headcount or row count: `9012` → `"9,012"`. */
export function formatCount(count: number): string {
  return COUNT.format(count);
}
