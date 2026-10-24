import { describe, expect, it } from "vitest";

import { formatMoney } from "./money";

describe("formatMoney", () => {
  it("shows minor units as major units with the currency symbol", () => {
    const text = formatMoney(5_400_050, "EUR");

    expect(text).toBe("€54,000.50");
  });

  it("shows yen with no decimals, because JPY has no minor unit", () => {
    const text = formatMoney(7_200_000, "JPY");

    expect(text).toBe("¥7,200,000");
  });

  it("leaves out minor units that are all zero, as on the printout", () => {
    const text = formatMoney(5_400_000, "EUR");

    expect(text).toBe("€54,000");
  });

  it("keeps every minor digit when asked to, for columns that must line up", () => {
    const text = formatMoney(5_400_000, "EUR", { minorUnits: "always" });

    expect(text).toBe("€54,000.00");
  });

  it.each([
    { currency: "USD", text: "US$121,000" },
    { currency: "CAD", text: "CA$121,000" },
    { currency: "AUD", text: "A$121,000" },
    { currency: "SGD", text: "S$121,000" },
  ])(
    "tells $currency apart from other dollars: $text",
    ({ currency, text }) => {
      expect(formatMoney(12_100_000, currency)).toBe(text);
    },
  );

  it("groups rupees in lakhs and crores, as Indian readers expect", () => {
    const text = formatMoney(186_000_000, "INR");

    expect(text).toBe("₹18,60,000");
  });

  // Larger than Number.MAX_SAFE_INTEGER: a float would lose the last digits.
  it.each([
    { kind: "bigint", amount: BigInt("123456789012345678901") },
    { kind: "string", amount: "123456789012345678901" },
  ])("keeps every digit of a huge $kind amount", ({ amount }) => {
    expect(formatMoney(amount, "EUR")).toBe("€1,234,567,890,123,456,789.01");
  });

  it.each([
    { kind: "fraction", amount: 12.5 },
    { kind: "unsafe integer", amount: 2 ** 60 },
  ])("refuses a $kind number, because money is never a float", ({ amount }) => {
    expect(() => formatMoney(amount, "EUR")).toThrow(RangeError);
  });

  // BigInt() alone would read "" and "  " as 0, "0x1F" as 31 and "+5" as 5.
  it.each(["", "  ", "0x1F", " 42 ", "+5", "12.5", "1e3"])(
    "refuses the string %j, which is not a whole number of minor units",
    (amount) => {
      expect(() => formatMoney(amount, "EUR")).toThrow(RangeError);
    },
  );

  // Monthly = annual ÷ 12, rounded half-even at the minor unit (display only).
  it.each([
    { annual: 5_400_000, currency: "EUR", monthly: "€4,500" },
    { annual: 100, currency: "EUR", monthly: "€0.08" }, // 8.33 rounds down
    { annual: 5_400_010, currency: "EUR", monthly: "€4,500.01" }, // 450,000.83 rounds up
    { annual: 18, currency: "EUR", monthly: "€0.02" }, // 1.5 ties to even 2
    { annual: 30, currency: "EUR", monthly: "€0.02" }, // 2.5 ties to even 2
    { annual: 7_200_006, currency: "JPY", monthly: "¥600,000" }, // 600,000.5 ties to even
  ])(
    "shows $annual $currency a year as $monthly a month",
    ({ annual, currency, monthly }) => {
      expect(formatMoney(annual, currency, { period: "monthly" })).toBe(
        monthly,
      );
    },
  );

  // A salary decrease is a negative change; it rounds like the positive amount.
  it.each([
    { amount: -150, period: "annual", text: "-€1.50" },
    { amount: -18, period: "monthly", text: "-€0.02" },
  ] as const)(
    "shows $amount ($period) as $text",
    ({ amount, period, text }) => {
      expect(formatMoney(amount, "EUR", { period })).toBe(text);
    },
  );

  // Compact notation is for charts and short sentences; tables show full values.
  it.each([
    { amount: 82_350_000_000, currency: "USD", text: "US$823.5M" },
    { amount: 125_000_000, currency: "EUR", text: "€1.2M" }, // 1.25 ties to even
    { amount: 186_000_000, currency: "INR", text: "₹18.6L" },
    { amount: -1, currency: "EUR", text: "€0" }, // rounds to zero: no "-€0"
  ])(
    "shortens $amount $currency to $text in compact mode",
    ({ amount, currency, text }) => {
      expect(formatMoney(amount, currency, { compact: true })).toBe(text);
    },
  );

  it("follows a locale it is given, with a non-breaking space before the symbol", () => {
    const text = formatMoney(5_400_050, "EUR", { locale: "de-DE" });

    expect(text).toBe("54.000,50\u00a0€");
  });
});
