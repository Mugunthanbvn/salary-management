import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { Me } from "@/lib/permissions";
import { makeMe } from "@/test/fixtures";

import { AppHeader } from "./app-header";
import { BottomNav } from "./bottom-nav";
import { MeProvider } from "./me-context";

const route = vi.hoisted(() => ({ pathname: "/insights" }));
vi.mock("next/navigation", () => ({
  usePathname: () => route.pathname,
  useRouter: () => ({ refresh: vi.fn() }),
}));

function renderShell(me: Me) {
  return render(
    <MeProvider me={me}>
      <AppHeader />
      <BottomNav />
    </MeProvider>,
  );
}

function mainNavs() {
  return screen.getAllByRole("navigation", { name: "Main" });
}

describe("main navigation", () => {
  it("links to Insights, Employees and Ask in the top bar and the phone bar", () => {
    renderShell(makeMe());

    const navs = mainNavs();
    expect(navs).toHaveLength(2);
    for (const nav of navs) {
      const links = within(nav).getAllByRole("link");
      expect(links.map((link) => link.textContent)).toEqual([
        "Insights",
        "Employees",
        "Ask",
      ]);
    }
  });

  it.each([
    { why: "Ask is switched off", me: makeMe({ features: { ask: false } }) },
    {
      why: "the person lacks the ASK permission",
      me: makeMe({ permissions: ["EMPLOYEE_READ", "INSIGHTS_READ"] }),
    },
  ])("hides Ask when $why", ({ me }) => {
    renderShell(me);

    for (const nav of mainNavs()) {
      expect(within(nav).queryByRole("link", { name: "Ask" })).toBeNull();
    }
  });
});
