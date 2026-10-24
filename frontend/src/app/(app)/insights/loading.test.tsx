import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import InsightsLoading from "./loading";
import PayEquityLoading from "./pay-equity/loading";

describe("insights loading states", () => {
  it.each([
    { route: "/insights", Loading: InsightsLoading, sections: 4 },
    { route: "/insights/pay-equity", Loading: PayEquityLoading, sections: 2 },
  ])(
    "$route says it is loading, in the page's own shape",
    ({ Loading, sections }) => {
      const { container } = render(<Loading />);

      expect(screen.getByRole("status")).toHaveTextContent("Loading…");
      expect(container.querySelector('[aria-busy="true"]')).not.toBeNull();
      expect(
        container.querySelectorAll("[data-skeleton-section]"),
      ).toHaveLength(sections);
    },
  );
});
