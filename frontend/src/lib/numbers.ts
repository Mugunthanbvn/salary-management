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

export function formatPercent(
  ratio: string,
  options: { fractionDigits?: number } = {},
): string {
  void ratio;
  void options;
  throw new Error("formatPercent is not implemented yet");
}
