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
});
