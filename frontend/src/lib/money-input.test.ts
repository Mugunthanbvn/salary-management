import { describe, expect, it } from "vitest";

import { toMajorInput, toMinorUnits } from "./money-input";

describe("toMinorUnits", () => {
  it.each([
    { input: "54000", currency: "EUR", exponent: 2, minor: 5_400_000 },
    { input: "54000.5", currency: "EUR", exponent: 2, minor: 5_400_050 },
    { input: "54,000.50", currency: "EUR", exponent: 2, minor: 5_400_050 },
    { input: " 21,60,000 ", currency: "INR", exponent: 2, minor: 216_000_000 },
    { input: "0.07", currency: "USD", exponent: 2, minor: 7 },
    { input: ".5", currency: "GBP", exponent: 2, minor: 50 },
    { input: "6000000", currency: "JPY", exponent: 0, minor: 6_000_000 },
    { input: "1000.0", currency: "JPY", exponent: 0, minor: 1000 },
    { input: "0", currency: "EUR", exponent: 2, minor: 0 },
  ])(
    "turns $input $currency into $minor minor units",
    ({ input, currency, exponent, minor }) => {
      expect(toMinorUnits(input, currency, exponent)).toEqual({
        ok: true,
        minor,
      });
    },
  );

  it("rejects more decimals than the currency allows, with the API's message", () => {
    expect(toMinorUnits("12.345", "EUR", 2)).toEqual({
      ok: false,
      message: "12.345 has more decimals than EUR allows",
    });
  });

  it("rejects any decimals for yen", () => {
    expect(toMinorUnits("1000.5", "JPY", 0)).toEqual({
      ok: false,
      message: "1000.5 has more decimals than JPY allows",
    });
  });

  it("keeps every digit of a large amount, which a float would round", () => {
    // 9007199254740.99 is not exact as a float: 9007199254740.99 * 100 = 900719925474099.1
    expect(toMinorUnits("9007199254740.99", "USD", 2)).toEqual({
      ok: true,
      minor: 900_719_925_474_099,
    });
  });

  it("refuses an amount too large to send exactly", () => {
    expect(toMinorUnits("90071992547409.93", "USD", 2)).toEqual({
      ok: false,
      message: "This amount is too large",
    });
  });

  it.each(["", "   "])(
    "asks for an amount when the field is empty (%j)",
    (input) => {
      expect(toMinorUnits(input, "EUR", 2)).toEqual({
        ok: false,
        message: "Enter an amount",
      });
    },
  );

  it.each(["abc", "-5", "1e5", "12.3.4", "€500", "."])(
    "refuses %j, which is not an amount",
    (input) => {
      expect(toMinorUnits(input, "EUR", 2)).toEqual({
        ok: false,
        message: "Enter a number, like 54000.50",
      });
    },
  );

  it("gives a yen example without decimals", () => {
    expect(toMinorUnits("abc", "JPY", 0)).toEqual({
      ok: false,
      message: "Enter a number, like 6000000",
    });
  });
});

describe("toMajorInput", () => {
  it.each([
    { minor: 5_400_000, exponent: 2, text: "54000" },
    { minor: 5_400_050, exponent: 2, text: "54000.50" },
    { minor: 7, exponent: 2, text: "0.07" },
    { minor: 6_000_000, exponent: 0, text: "6000000" },
    { minor: 0, exponent: 2, text: "0" },
  ])(
    "writes $minor minor units as $text for an input field",
    ({ minor, exponent, text }) => {
      expect(toMajorInput(minor, exponent)).toBe(text);
    },
  );

  it("reads back to the same minor units", () => {
    const text = toMajorInput(900_719_925_474_099, 2);

    expect(toMinorUnits(text, "USD", 2)).toEqual({
      ok: true,
      minor: 900_719_925_474_099,
    });
  });
});
