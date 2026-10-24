/**
 * Display formatting for the non-money numbers the API sends. Ratios arrive as decimal
 * strings (`"0.9234"`) and are formatted from that exact string, never through a float,
 * rounding half-even like the API. The locale is fixed, so server and browser agree.
 */

const RATIO = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
  roundingMode: "halfEven",
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
  return new Intl.NumberFormat("en-US", {
    style: "percent",
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
    roundingMode: "halfEven",
  }).format(ratio as Intl.StringNumericLiteral);
}

export function formatCount(count: number): string {
  void count;
  throw new Error("formatCount is not implemented yet");
}
