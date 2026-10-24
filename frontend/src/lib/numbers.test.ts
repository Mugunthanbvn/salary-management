import { describe, expect, it } from "vitest";

import { formatRatio } from "./numbers";

describe("formatRatio", () => {
  // Ratios such as the compa-ratio arrive from the API as decimal strings.
  it.each([
    { ratio: "0.9234", text: "0.92" },
    { ratio: "1.2", text: "1.20" },
    { ratio: "0.925", text: "0.92" }, // ties to even
    { ratio: "0.935", text: "0.94" }, // ties to even
  ])("shows $ratio as $text", ({ ratio, text }) => {
    expect(formatRatio(ratio)).toBe(text);
  });
});
