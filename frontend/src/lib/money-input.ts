/**
 * The one conversion the UI does on money: an amount the person typed in major units
 * ("54,000.50") becomes integer minor units for the API (5400050), and back for pre-filled
 * fields. String maths only, never a float: the digits are moved, not multiplied.
 * The exponent comes from GET /reference (`currencies[].exponent`).
 */

export type MinorUnitsResult =
  { ok: true; minor: number } | { ok: false; message: string };

// Digits with an optional fraction ("54000", "54000.50", ".5"), once group separators are gone.
const AMOUNT = /^(\d*)(?:\.(\d*))?$/;

// Thousands ("54,000,000") or Indian lakh grouping ("2,16,00,000"), then an optional fraction.
const GROUPED = /^(?:\d{1,3}(?:,\d{3})+|\d{1,2}(?:,\d{2})*,\d{3})(?:\.\d*)?$/;

/** The API's MAX_AMOUNT_MINOR (10^15 − 1), so a too-large amount fails here, not there. */
const MAX_AMOUNT_MINOR = BigInt(10) ** BigInt(15) - BigInt(1);

/**
 * "54,000.50" EUR (exponent 2) → 5400050. Commas and spaces are group separators; "." is
 * the decimal point. More decimals than the currency allows are refused, never rounded,
 * with the API's message; trailing zeros are fine ("1000.0" JPY is ¥1,000).
 */
export function toMinorUnits(
  input: string,
  currency: string,
  exponent: number,
): MinorUnitsResult {
  const spaced = input.replace(/\s/g, "");
  if (!spaced) return { ok: false, message: "Enter an amount" };
  // A comma only groups digits: "54,000.50" or "21,60,000", never "1,5" or "1500,50".
  if (spaced.includes(",") && !GROUPED.test(spaced)) {
    return { ok: false, message: "Use . for decimals" };
  }
  const text = spaced.replace(/,/g, "");
  const match = AMOUNT.exec(text);
  const whole = match?.[1] ?? "";
  const fraction = match?.[2] ?? "";
  if (!match || (!whole && !fraction)) {
    return { ok: false, message: `Enter a number, like ${example(exponent)}` };
  }
  const significant = fraction.replace(/0+$/, "");
  if (significant.length > exponent) {
    return {
      ok: false,
      message: `${text} has more decimals than ${currency} allows`,
    };
  }
  const minor = BigInt(whole + significant.padEnd(exponent, "0"));
  if (minor > MAX_AMOUNT_MINOR) {
    return { ok: false, message: "This amount is too large" };
  }
  return { ok: true, minor: Number(minor) };
}

/** 5400050 minor units (exponent 2) → "54000.50"; a whole amount has no fraction: "54000". */
export function toMajorInput(minor: number, exponent: number): string {
  const digits = BigInt(minor)
    .toString()
    .padStart(exponent + 1, "0");
  const cut = digits.length - exponent;
  const whole = digits.slice(0, cut);
  const fraction = digits.slice(cut);
  return /^0*$/.test(fraction) ? whole : `${whole}.${fraction}`;
}

function example(exponent: number): string {
  return exponent === 0 ? "6000000" : `54000.${"5".padEnd(exponent, "0")}`;
}
