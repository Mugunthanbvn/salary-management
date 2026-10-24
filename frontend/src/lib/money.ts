/**
 * Display formatting for money from the API (`{ amount_minor, currency }`).
 * No float maths: the amount stays a BigInt and is split into major and minor units with
 * string maths, then Intl.NumberFormat formats the exact decimal string.
 */
export type FormatMoneyOptions = {
  /** Stored amounts are annual; "monthly" shows annual ÷ 12, rounded half-even. */
  period?: "annual" | "monthly";
  /** Short form for charts and sentences ("US$823.5M"); tables show full values. */
  compact?: boolean;
  /** Overrides the fixed default (en-US, or en-IN for rupees). */
  locale?: string;
  /** "auto" (default) leaves out minor units that are all zero; "always" keeps them. */
  minorUnits?: "auto" | "always";
};

export function formatMoney(
  amountMinor: number | bigint | string,
  currency: string,
  {
    period = "annual",
    compact = false,
    minorUnits = "auto",
    locale = defaultLocale(currency),
  }: FormatMoneyOptions = {},
): string {
  const annual = toBigInt(amountMinor);
  const amount =
    period === "monthly" ? divideHalfEven(annual, MONTHS_PER_YEAR) : annual;
  const { major, fraction } = splitMinor(amount, minorDigits(currency));
  // Whole amounts read like the printout ("€54,000"); any minor part shows every digit.
  const fractionDigits =
    minorUnits === "auto" && /^0*$/.test(fraction) ? 0 : fraction.length;
  const formatter = new Intl.NumberFormat(locale, {
    style: "currency",
    currency,
    ...(compact
      ? {
          notation: "compact",
          minimumFractionDigits: 0,
          maximumFractionDigits: 1,
          roundingMode: "halfEven",
        }
      : {
          minimumFractionDigits: fractionDigits,
          maximumFractionDigits: fractionDigits,
        }),
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

/** Money arrives as integer minor units; a fraction or an imprecise number is a bug. */
function toBigInt(amountMinor: number | bigint | string): bigint {
  if (typeof amountMinor === "number" && !Number.isSafeInteger(amountMinor)) {
    throw new RangeError(
      `Money must be a safe integer of minor units, got ${amountMinor}`,
    );
  }
  return BigInt(amountMinor);
}

const MONTHS_PER_YEAR = BigInt(12);

/** Integer division of minor units, rounding half to even (the sign rounds symmetrically). */
function divideHalfEven(dividend: bigint, divisor: bigint): bigint {
  const negative = dividend < BigInt(0);
  const magnitude = negative ? -dividend : dividend;
  let quotient = magnitude / divisor;
  const twiceRemainder = (magnitude % divisor) * BigInt(2);
  const odd = quotient % BigInt(2) === BigInt(1);
  if (twiceRemainder > divisor || (twiceRemainder === divisor && odd)) {
    quotient += BigInt(1);
  }
  return negative ? -quotient : quotient;
}

/**
 * A fixed locale, so the server and the browser render the same text. Rupees use Indian
 * grouping (₹18,60,000); everything else uses en-US grouping (€54,000).
 */
function defaultLocale(currency: string): string {
  return currency === "INR" ? "en-IN" : "en-US";
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
  const sign = minor < BigInt(0) ? "-" : "";
  const digits = (sign ? -minor : minor).toString().padStart(exponent + 1, "0");
  const cut = digits.length - exponent;
  return { major: sign + digits.slice(0, cut), fraction: digits.slice(cut) };
}
