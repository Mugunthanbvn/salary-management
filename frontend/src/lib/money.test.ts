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
});
