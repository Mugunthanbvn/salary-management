import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { HIDDEN_REASON } from "@/components/insights/figures";
import { API_ORIGIN } from "@/lib/api/origin";
import type { components } from "@/lib/api/schema";
import type { Me } from "@/lib/permissions";
import {
  makeMe,
  makeProblem,
  makeReference,
  makeViewer,
} from "@/test/fixtures";
import {
  makeCohort,
  makeCohortMembers,
  makePayEquityCohorts,
  makePayEquityDepartments,
  suppressedStats,
} from "@/test/insights-fixtures";
import { server } from "@/test/msw/server";
import { renderInApp } from "@/test/render";
import { signedInRequest } from "@/test/server";

import PayEquityPage from "./page";

type S = components["schemas"];

const { getMe } = vi.hoisted(() => ({ getMe: vi.fn<() => Promise<Me>>() }));
vi.mock("@/lib/api/me", () => ({ getMe }));
vi.mock("next/headers", () => ({ cookies: vi.fn() }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn(), push: vi.fn() }),
}));

const PAY_EQUITY = `${API_ORIGIN}/api/v1/insights/pay-equity`;

function serveReference() {
  server.use(
    http.get<never, never, S["ReferenceData"]>(
      `${API_ORIGIN}/api/v1/reference`,
      () => HttpResponse.json(makeReference()),
    ),
  );
}

/** Serves both pay-equity views; returns each request's query, by view. */
function servePayEquity({
  cohorts = makePayEquityCohorts(),
  departments = makePayEquityDepartments(),
}: {
  cohorts?: S["PayEquityCohorts"];
  departments?: S["PayEquityDepartments"];
} = {}) {
  serveReference();
  const seen: Record<string, URLSearchParams> = {};
  server.use(
    http.get<never, never, S["PayEquityCohorts"] | S["PayEquityDepartments"]>(
      PAY_EQUITY,
      ({ request }) => {
        const query = new URL(request.url).searchParams;
        const view = query.get("view") ?? "cohorts";
        seen[view] = query;
        return HttpResponse.json(
          view === "departments" ? departments : cohorts,
        );
      },
    ),
  );
  return seen;
}

async function renderPage(
  search: Record<string, string> = {},
  me: Me = makeMe(),
) {
  getMe.mockResolvedValue(me);
  signedInRequest();
  const page = await PayEquityPage({
    params: Promise.resolve({}),
    searchParams: Promise.resolve(search),
  });
  renderInApp(page, {
    me,
    searchParams: `?${new URLSearchParams(search).toString()}`,
  });
}

const TEAMS = "Is any team paid below its bands?";
const COHORTS = "Which roles and levels?";

describe("/insights/pay-equity", () => {
  it("asks for a country before comparing anyone with their bands", async () => {
    // No pay-equity handler: asking for it would fail the test.
    serveReference();

    await renderPage();

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: "Are we paying people fairly?",
      }),
    ).toBeVisible();
    expect(screen.getByRole("link", { name: "Germany" })).toHaveAttribute(
      "href",
      "/insights/pay-equity?country=DE",
    );
  });

  it("asks both views for the URL's country and department", async () => {
    const seen = servePayEquity();

    await renderPage({ country: "DE", department_id: "4" });

    expect(seen.departments?.getAll("country")).toEqual(["DE"]);
    expect(seen.departments?.getAll("department_id")).toEqual(["4"]);
    expect(seen.cohorts?.getAll("country")).toEqual(["DE"]);
    expect(seen.cohorts?.getAll("department_id")).toEqual(["4"]);
    expect(
      screen.getByRole("heading", {
        level: 1,
        name: "Are we paying Germany fairly?",
      }),
    ).toBeVisible();
  });

  it("sums up who was evaluated, who was left out and who is flagged", async () => {
    servePayEquity();

    await renderPage({ country: "DE" });

    expect(
      screen.getByRole("heading", { level: 1 }).parentElement,
    ).toHaveTextContent(
      "702 full-time employees in Germany were compared with their pay bands: 31 are paid below their band and 12 above it. 48 who aren't full-time are left out, and 0 have no band.",
    );
  });

  it("flags the team whose median is below its bands, in words", async () => {
    servePayEquity();

    await renderPage({ country: "DE" });

    const teams = screen.getByRole("region", { name: TEAMS });
    expect(teams).toHaveTextContent(
      "Yes. Customer Success has a median compa-ratio of 0.93",
    );
    const customerSuccess = within(teams).getByRole("row", {
      name: /Customer Success/,
    });
    expect(customerSuccess).toHaveTextContent("0.93");
    expect(customerSuccess).toHaveTextContent("29%");
    expect(customerSuccess).toHaveTextContent("Below band as a team");
    expect(
      within(teams).getByRole("row", { name: /Engineering/ }),
    ).not.toHaveTextContent("Below band");
  });

  it("says no team is below its bands when none is", async () => {
    servePayEquity({
      departments: makePayEquityDepartments({
        groups: makePayEquityDepartments().groups.map((group) => ({
          ...group,
          below_threshold: false,
          median_compa_ratio: "1.00",
        })),
      }),
    });

    await renderPage({ country: "DE" });

    expect(screen.getByRole("region", { name: TEAMS })).toHaveTextContent(
      "No. Every team's median compa-ratio is at least 0.95",
    );
  });

  it("shows each role and level against its band", async () => {
    servePayEquity();

    await renderPage({ country: "DE" });

    const cohorts = screen.getByRole("region", { name: COHORTS });
    const row = within(cohorts).getByRole("listitem", {
      name: "Customer Success Manager, L2",
    });
    expect(row).toHaveTextContent("Band €41,760 to €62,640");
    expect(row).toHaveTextContent("Median €47,000");
    expect(row).toHaveTextContent("0.90");
    expect(row).toHaveTextContent("5 below band");
    expect(
      within(cohorts).getByRole("listitem", { name: "Software Engineer, L3" }),
    ).toHaveTextContent("3 above band");
  });

  it("lists the most flagged roles first", async () => {
    servePayEquity({
      cohorts: makePayEquityCohorts({
        cohorts: [
          makeCohort({
            job_role: { id: 5, title: "Software Engineer" },
            level: "L3",
            underpaid_count: 0,
            overpaid_count: 1,
          }),
          makeCohort({ underpaid_count: 7, overpaid_count: 0 }),
        ],
      }),
    });

    await renderPage({ country: "DE" });

    const items = within(
      screen.getByRole("region", { name: COHORTS }),
    ).getAllByRole("listitem");
    expect(items[0]).toHaveAccessibleName("Customer Success Manager, L2");
  });

  describe("for a viewer", () => {
    it("shows counts and ratios but no way to see people", async () => {
      servePayEquity();

      await renderPage({ country: "DE" }, makeViewer());

      const cohorts = screen.getByRole("region", { name: COHORTS });
      expect(within(cohorts).getByText("0.90")).toBeVisible();
      expect(
        within(cohorts).queryByRole("button", { name: /See the/ }),
      ).not.toBeInTheDocument();
    });

    it("shows a small cohort as dashes", async () => {
      servePayEquity({
        cohorts: makePayEquityCohorts({
          cohorts: [
            makeCohort({
              stats: suppressedStats(),
              median_compa_ratio: null,
              underpaid_count: null,
              overpaid_count: null,
              suppressed: true,
            }),
          ],
        }),
      });

      await renderPage({ country: "DE" }, makeViewer());

      const row = within(
        screen.getByRole("region", { name: COHORTS }),
      ).getByRole("listitem", { name: "Customer Success Manager, L2" });
      expect(
        within(row).getAllByRole("button", { name: HIDDEN_REASON }).length,
      ).toBeGreaterThanOrEqual(2);
      // The band is policy, not anyone's pay: it stays visible.
      expect(row).toHaveTextContent("Band €41,760 to €62,640");
    });

    it("tells a screen reader why the middle half is hidden, without an unseen button", async () => {
      servePayEquity({
        cohorts: makePayEquityCohorts({
          cohorts: [makeCohort({ stats: suppressedStats(), suppressed: true })],
        }),
      });

      await renderPage({ country: "DE" }, makeViewer());

      const row = within(
        screen.getByRole("region", { name: COHORTS }),
      ).getByRole("listitem", { name: "Customer Success Manager, L2" });
      const middleHalf = within(row).getByText(/^Middle half earns/);
      expect(middleHalf).toHaveTextContent(
        "Middle half earns: hidden to protect individual pay (fewer than 5 people)",
      );
      expect(within(middleHalf).queryByRole("button")).toBeNull();
    });
  });

  it("opens a cohort for HR and lists its people with their compa-ratio", async () => {
    const user = userEvent.setup();
    servePayEquity();
    let asked: URLSearchParams | null = null;
    server.use(
      http.get<never, never, S["CohortMembers"]>(
        "/api/v1/insights/pay-equity/cohort",
        ({ request }) => {
          asked = new URL(request.url).searchParams;
          return HttpResponse.json(makeCohortMembers());
        },
      ),
    );
    await renderPage({ country: "DE" });

    await user.click(
      screen.getByRole("button", {
        name: "See the 18 people in Customer Success Manager, L2",
      }),
    );

    const sheet = await screen.findByRole("dialog", {
      name: "Customer Success Manager, L2 in Germany",
    });
    const lukas = await within(sheet).findByRole("listitem", {
      name: "Lukas Weber",
    });
    expect(lukas).toHaveTextContent("€36,500");
    expect(lukas).toHaveTextContent("0.70");
    expect(lukas).toHaveTextContent("Below band");
    expect(
      within(lukas).getByRole("link", { name: "Lukas Weber" }),
    ).toHaveAttribute("href", "/employees/3412");
    expect(
      within(sheet).getByRole("listitem", { name: "Hannah Meyer" }),
    ).toHaveTextContent("In band");
    expect(asked).not.toBeNull();
    expect(Object.fromEntries(asked!)).toEqual({
      job_role_id: "17",
      level: "L2",
      country: "DE",
    });
  });

  it("shows the problem in the sheet when a cohort can't be opened", async () => {
    const user = userEvent.setup();
    servePayEquity();
    server.use(
      http.get<never, never, S["Problem"]>(
        "/api/v1/insights/pay-equity/cohort",
        () =>
          HttpResponse.json(
            makeProblem("internal", 503, {
              title: "Service unavailable",
              request_id: "req-cohort",
            }),
            { status: 503 },
          ),
      ),
    );
    await renderPage({ country: "DE" });

    await user.click(
      screen.getByRole("button", {
        name: "See the 18 people in Customer Success Manager, L2",
      }),
    );

    const sheet = await screen.findByRole("dialog");
    expect(await within(sheet).findByRole("alert")).toHaveTextContent(
      "Request ID: req-cohort",
    );
  });

  it("shows a failed view as a problem with its request id", async () => {
    servePayEquity();
    server.use(
      http.get<never, never, S["Problem"]>(PAY_EQUITY, () =>
        HttpResponse.json(
          makeProblem("internal", 503, {
            title: "Service unavailable",
            request_id: "req-pe",
          }),
          { status: 503 },
        ),
      ),
    );

    await renderPage({ country: "DE" });

    expect(
      within(screen.getByRole("region", { name: TEAMS })).getByRole("alert"),
    ).toHaveTextContent("Request ID: req-pe");
  });
});
