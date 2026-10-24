import { describe, expect, it } from "vitest";

import { formatCount, formatPercent, formatRatio } from "./numbers";

describe("formatRatio", () => {
  // Ratios such as the compa-ratio arrive from the API as decimal strings.
  it.each([
    { ratio: "0.9234", text: "0.92" },
    { ratio: "1.2", text: "1.20" },
    { ratio: "0.925", text: "0.92" }, // ties to even
    { ratio: "0.935", text: "0.94" }, // ties to even
    { ratio: "-0.001", text: "0.00" }, // rounds to zero: no "-0.00"
  ])("shows $ratio as $text", ({ ratio, text }) => {
    expect(formatRatio(ratio)).toBe(text);
  });
});

describe("formatPercent", () => {
  it.each([
    { ratio: "0.08", digits: undefined, text: "8%" },
    { ratio: "0.4412", digits: undefined, text: "44%" },
    { ratio: "0.0825", digits: 1, text: "8.2%" }, // ties to even
    { ratio: "-0.08", digits: undefined, text: "-8%" },
    { ratio: "-0.001", digits: undefined, text: "0%" }, // rounds to zero: no "-0%"
  ])("shows $ratio as $text", ({ ratio, digits, text }) => {
    expect(formatPercent(ratio, { fractionDigits: digits })).toBe(text);
  });
});

describe("formatCount", () => {
  it("groups a headcount the same way on the server and in the browser", () => {
    expect(formatCount(9012)).toBe("9,012");
  });
});
