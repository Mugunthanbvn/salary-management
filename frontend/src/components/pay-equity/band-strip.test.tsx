import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { THRESHOLDS } from "@/test/insights-fixtures";

import { BandStrip, RatioStrip } from "./band-strip";

const BAND = {
  min: 4_000_000,
  mid: 5_000_000,
  max: 6_000_000,
  currency: "EUR",
};

function mark(container: HTMLElement, name: string) {
  const element = container.querySelector<HTMLElement>(`[data-mark="${name}"]`);
  if (!element) throw new Error(`no ${name} mark`);
  return element.style;
}

describe("BandStrip", () => {
  it("draws the band, its middle, the middle half and the median where the API puts them", () => {
    const { container } = render(
      <BandStrip
        band={BAND}
        stats={{ p25: 4_500_000, median: 5_000_000, p75: 5_500_000 }}
      />,
    );

    expect(mark(container, "band")).toMatchObject({
      left: "0%",
      width: "100%",
    });
    expect(mark(container, "mid").left).toBe("50%");
    expect(mark(container, "middle-half")).toMatchObject({
      left: "25%",
      width: "50%",
    });
    expect(mark(container, "median").left).toBe("50%");
  });

  it("widens the scale so pay below the band shows outside it", () => {
    const { container } = render(
      <BandStrip
        band={BAND}
        stats={{ p25: 2_000_000, median: 4_000_000, p75: 5_000_000 }}
      />,
    );

    // Scale 2,000,000 to 6,000,000: the band starts half way along.
    expect(mark(container, "band")).toMatchObject({
      left: "50%",
      width: "50%",
    });
    expect(mark(container, "median").left).toBe("50%");
    expect(mark(container, "middle-half").left).toBe("0%");
  });

  it("draws no pay marks for a hidden cohort, only its band", () => {
    const { container } = render(
      <BandStrip band={BAND} stats={{ p25: null, median: null, p75: null }} />,
    );

    expect(container.querySelector('[data-mark="median"]')).toBeNull();
    expect(container.querySelector('[data-mark="middle-half"]')).toBeNull();
    expect(mark(container, "band").width).toBe("100%");
  });
});

describe("RatioStrip", () => {
  it("puts a team's median compa-ratio on the API's low-to-high scale", () => {
    const { container } = render(
      <RatioStrip ratio="0.93" thresholds={THRESHOLDS} flagged />,
    );

    expect(parseFloat(mark(container, "ratio").left)).toBeCloseTo(32.5);
  });
});
