import { describe, expect, it } from "vitest";

import { positionPercent, stripScale } from "./position";

describe("positionPercent", () => {
  it("places a value along a scale as a percentage of its width", () => {
    expect(positionPercent(5_400_000, 4_320_000, 6_480_000)).toBe(50);
    expect(positionPercent(4_320_000, 4_320_000, 6_480_000)).toBe(0);
    expect(positionPercent(6_480_000, 4_320_000, 6_480_000)).toBe(100);
  });

  it("reads the API's decimal-string ratios", () => {
    expect(positionPercent("0.93", "0.80", "1.20")).toBeCloseTo(32.5);
    expect(positionPercent("1.00", "0.80", "1.20")).toBe(50);
  });

  it("keeps a value outside the scale on its edge", () => {
    expect(positionPercent("0.62", "0.80", "1.20")).toBe(0);
    expect(positionPercent("1.45", "0.80", "1.20")).toBe(100);
  });

  it("puts everything in the middle of a scale with no width", () => {
    expect(positionPercent(10, 10, 10)).toBe(50);
  });
});

describe("stripScale", () => {
  it("spans the band when the cohort's pay sits inside it", () => {
    expect(
      stripScale({ min: 4_000_000, max: 6_000_000 }, [4_500_000, 5_500_000]),
    ).toEqual({ lo: 4_000_000, hi: 6_000_000 });
  });

  it("widens to show pay that falls outside the band", () => {
    expect(
      stripScale({ min: 4_000_000, max: 6_000_000 }, [3_500_000, 6_200_000]),
    ).toEqual({ lo: 3_500_000, hi: 6_200_000 });
  });

  it("ignores figures the API hid", () => {
    expect(
      stripScale({ min: 4_000_000, max: 6_000_000 }, [null, null]),
    ).toEqual({ lo: 4_000_000, hi: 6_000_000 });
  });
});
