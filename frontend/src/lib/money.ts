/**
 * Display formatting for money from the API (`{ amount_minor, currency }`).
 * No float maths: the amount stays a BigInt and is split into major and minor units with
 * string maths, then Intl.NumberFormat formats the exact decimal string.
 */
export type FormatMoneyOptions = {
  /** "auto" (default) leaves out minor units that are all zero; "always" keeps them. */
  minorUnits?: "auto" | "always";
};

export function formatMoney(
  amountMinor: number | bigint | string,
  currency: string,
  { minorUnits = "auto" }: FormatMoneyOptions = {},
): string {
  const { major, fraction } = splitMinor(
    BigInt(amountMinor),
    minorDigits(currency),
  );
  // Whole amounts read like the printout ("€54,000"); any minor part shows every digit.
  const fractionDigits =
    minorUnits === "auto" && /^0*$/.test(fraction) ? 0 : fraction.length;
  const formatter = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  });
  const decimal = fraction ? `${major}.${fraction}` : major;
  return withSymbol(
    formatter.formatToParts(decimal as Intl.StringNumericLiteral),
    currency,
  );
}

/** "$" alone is ambiguous: say whose dollar it is (docs/13-frontend-ux.md §3.3). */
const DOLLAR_SYMBOLS: Record<string, string> = {
  USD: "US$",
  CAD: "CA$",
  AUD: "A$",
  SGD: "S$",
};

function withSymbol(parts: Intl.NumberFormatPart[], currency: string): string {
  const symbol = DOLLAR_SYMBOLS[currency];
  return parts
    .map((part, index) => {
      if (!symbol) return part.value;
      if (part.type === "currency") return symbol;
      // "SGD 121,000" becomes "S$121,000": no gap after a prefix symbol.
      const afterSymbol = parts[index - 1]?.type === "currency";
      return afterSymbol && part.type === "literal" && !part.value.trim()
        ? ""
        : part.value;
    })
    .join("");
}

/** The currency's minor-unit exponent (JPY 0, EUR 2), as Intl knows it. */
function minorDigits(currency: string): number {
  const options = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
  }).resolvedOptions();
  return options.maximumFractionDigits ?? 2;
}

/** 5400050n with exponent 2 → { major: "54000", fraction: "50" }, by string maths. */
function splitMinor(
  minor: bigint,
  exponent: number,
): { major: string; fraction: string } {
  const digits = minor.toString().padStart(exponent + 1, "0");
  const cut = digits.length - exponent;
  return { major: digits.slice(0, cut), fraction: digits.slice(cut) };
}
