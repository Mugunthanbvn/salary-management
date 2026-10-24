/**
 * Display formatting for money from the API (`{ amount_minor, currency }`).
 * No float maths: the amount stays a BigInt and is split into major and minor units with
 * string maths, then Intl.NumberFormat formats the exact decimal string.
 */
export function formatMoney(
  amountMinor: number | bigint | string,
  currency: string,
): string {
  const minor = BigInt(amountMinor);
  const formatter = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
  });
  const exponent = formatter.resolvedOptions().maximumFractionDigits ?? 2;
  return formatter.format(toDecimalString(minor, exponent));
}

function toDecimalString(
  minor: bigint,
  exponent: number,
): Intl.StringNumericLiteral {
  const digits = minor.toString().padStart(exponent + 1, "0");
  const major = digits.slice(0, digits.length - exponent);
  const fraction = digits.slice(digits.length - exponent);
  return `${major}.${fraction}` as Intl.StringNumericLiteral;
}
