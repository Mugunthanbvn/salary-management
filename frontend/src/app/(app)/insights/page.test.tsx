import { screen, waitFor, within } from "@testing-library/react";
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
  makeByDepartment,
  makeByJobTitle,
  makeDepartmentCosts,
  makeOverview,
  makeStats,
  makeTopEarners,
  suppressedStats,
  viewerStats,
} from "@/test/insights-fixtures";
import { server } from "@/test/msw/server";
import { renderInApp } from "@/test/render";
import { signedInRequest } from "@/test/server";

import InsightsPage from "./page";

type S = components["schemas"];

const { getMe } = vi.hoisted(() => ({ getMe: vi.fn<() => Promise<Me>>() }));
vi.mock("@/lib/api/me", () => ({ getMe }));
vi.mock("next/headers", () => ({ cookies: vi.fn() }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn(), push: vi.fn() }),
}));

type Bodies = {
  overview?: S["Overview"];
  byDepartment?: S["ByDepartment"];
  departmentCost?: S["DepartmentCosts"];
  byJobTitle?: S["ByJobTitle"];
  topEarners?: S["TopEarners"];
};

/**
 * Serves GET /reference and the insight endpoints; records each request's query by path.
 * By-job-title and top earners are served only when given: any other call fails the test.
 */
function serveInsights(bodies: Bodies = {}) {
  const seen = new Map<string, URLSearchParams[]>();
  const record = (request: Request) => {
    const url = new URL(request.url);
    seen.set(url.pathname, [
      ...(seen.get(url.pathname) ?? []),
      url.searchParams,
    ]);
  };
  const insight = `${API_ORIGIN}/api/v1/insights`;
  server.use(
    http.get<never, never, S["ReferenceData"]>(
      `${API_ORIGIN}/api/v1/reference`,
      () => HttpResponse.json(makeReference()),
    ),
    http.get<never, never, S["Overview"]>(
      `${insight}/overview`,
      ({ request }) => {
        record(request);
        return HttpResponse.json(bodies.overview ?? makeOverview());
      },
    ),
    http.get<never, never, S["ByDepartment"]>(
      `${insight}/by-department`,
      ({ request }) => {
        record(request);
        return HttpResponse.json(bodies.byDepartment ?? makeByDepartment());
      },
    ),
    http.get<never, never, S["DepartmentCosts"]>(
      `${insight}/department-cost`,
      ({ request }) => {
        record(request);
        return HttpResponse.json(
          bodies.departmentCost ?? makeDepartmentCosts(),
        );
      },
    ),
  );
  if (bodies.byJobTitle) {
    const body = bodies.byJobTitle;
    server.use(
      http.get<never, never, S["ByJobTitle"]>(
        `${insight}/by-job-title`,
        ({ request }) => {
          record(request);
          return HttpResponse.json(body);
        },
      ),
    );
  }
  if (bodies.topEarners) {
    const body = bodies.topEarners;
    server.use(
      http.get<never, never, S["TopEarners"]>(
        `${insight}/top-earners`,
        ({ request }) => {
          record(request);
          return HttpResponse.json(body);
        },
      ),
    );
  }
  return seen;
}

type Search = Record<string, string | string[]>;

// A Server Component: call it with the page's search params, then render what it returns.
async function renderPage(
  search: Search = {},
  me: Me = makeMe(),
  onUrlUpdate?: ReturnType<typeof vi.fn>,
) {
  getMe.mockResolvedValue(me);
  signedInRequest();
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(search)) {
    for (const item of [value].flat()) query.append(key, item);
  }
  const page = await InsightsPage({
    params: Promise.resolve({}),
    searchParams: Promise.resolve(search),
  });
  renderInApp(page, { me, searchParams: `?${query.toString()}`, onUrlUpdate });
}

function section(name: string) {
  return screen.getByRole("region", { name });
}

const COUNTRY_QUESTION = "What does a typical employee earn in each country?";

describe("/insights", () => {
  it("asks every insight for the URL's population, filters and comp, never the period", async () => {
    const seen = serveInsights({
      byJobTitle: makeByJobTitle(),
      topEarners: makeTopEarners(),
    });

    await renderPage({
      country: "DE",
      department_id: "4",
      comp: "total",
      period: "monthly",
      employment_type: ["FULL_TIME", "PART_TIME"],
    });

    for (const path of [
      "overview",
      "by-department",
      "department-cost",
      "by-job-title",
      "top-earners",
    ]) {
      const [query] = seen.get(`/api/v1/insights/${path}`) ?? [];
      expect(query?.getAll("country"), path).toEqual(["DE"]);
      expect(query?.getAll("department_id"), path).toEqual(["4"]);
      expect(query?.get("comp"), path).toBe("total");
      expect(query?.getAll("employment_type"), path).toEqual([
        "FULL_TIME",
        "PART_TIME",
      ]);
      expect(query?.getAll("status"), path).toEqual(["ACTIVE"]);
      expect(query?.has("period"), path).toBe(false);
    }
  });

  it("sums up the org in one sentence with the payroll in US$ and the FX date", async () => {
    serveInsights();

    await renderPage();

    const heading = screen.getByRole("heading", {
      level: 1,
      name: "How ACME pays people",
    });
    expect(heading.parentElement).toHaveTextContent(
      "9,012 full-time, active employees in 2 countries, paid US$823.5M a year in base pay, at exchange rates of 1 Oct 2026.",
    );
  });

  it("shows each country's pay in its own currency, with US$ alongside", async () => {
    serveInsights();

    await renderPage();

    const table = within(section(COUNTRY_QUESTION)).getByRole("table");
    const germany = within(table).getByRole("row", { name: /Germany/ });
    expect(germany).toHaveTextContent("€54,000");
    expect(germany).toHaveTextContent("€48,000 to €63,000");
    expect(germany).toHaveTextContent("US$58,320");
    expect(germany).toHaveTextContent("702");
    const india = within(table).getByRole("row", { name: /India/ });
    expect(india).toHaveTextContent("₹18,60,000");
  });

  it("shows the lowest and highest pay to HR", async () => {
    serveInsights();

    await renderPage();

    const table = within(section(COUNTRY_QUESTION)).getByRole("table");
    expect(
      within(table).getByRole("columnheader", { name: "Lowest to highest" }),
    ).toBeVisible();
    expect(
      within(table).getByRole("row", { name: /Germany/ }),
    ).toHaveTextContent("€39,000 to €168,000");
  });

  it("shows money a month at a time when the URL says monthly", async () => {
    serveInsights();

    await renderPage({ period: "monthly" });

    const table = within(section(COUNTRY_QUESTION)).getByRole("table");
    expect(
      within(table).getByRole("row", { name: /Germany/ }),
    ).toHaveTextContent("€4,500");
    expect(
      screen.getByRole("heading", { level: 1 }).parentElement,
    ).toHaveTextContent("paid US$68.6M a month");
  });

  it("switches to monthly on screen without asking the API again", async () => {
    const user = userEvent.setup();
    const seen = serveInsights();
    await renderPage();
    const before = seen.get("/api/v1/insights/overview")?.length;

    await user.click(screen.getByRole("button", { name: "Monthly" }));

    const table = within(section(COUNTRY_QUESTION)).getByRole("table");
    await waitFor(() =>
      expect(
        within(table).getByRole("row", { name: /Germany/ }),
      ).toHaveTextContent("€4,500"),
    );
    expect(seen.get("/api/v1/insights/overview")?.length).toBe(before);
  });

  it("says when the figures are total pay", async () => {
    serveInsights();

    await renderPage({ comp: "total" });

    expect(
      screen.getByRole("heading", { level: 1 }).parentElement,
    ).toHaveTextContent("a year in total pay");
  });

  describe("for a viewer", () => {
    function viewerOverview() {
      const overview = makeOverview();
      return makeOverview({
        stats: viewerStats(overview.stats),
        by_country: [
          ...overview.by_country.map((row) => ({
            ...row,
            local: viewerStats(row.local),
            usd: viewerStats(row.usd),
          })),
          {
            country_code: "JP",
            local: suppressedStats("JPY"),
            usd: suppressedStats("USD"),
          },
        ],
      });
    }

    it("shows a small country as a dash that explains itself", async () => {
      serveInsights({ overview: viewerOverview() });

      await renderPage({}, makeViewer());

      const table = within(section(COUNTRY_QUESTION)).getByRole("table");
      const japan = within(table).getByRole("row", { name: /Japan/ });
      expect(
        within(japan).getAllByRole("button", { name: HIDDEN_REASON }).length,
      ).toBeGreaterThanOrEqual(3);
      expect(japan).not.toHaveTextContent("¥");
    });

    it("has no lowest or highest pay and no top earners", async () => {
      // No top-earners handler: asking for it would fail the test.
      serveInsights({
        overview: viewerOverview(),
        byJobTitle: makeByJobTitle(),
      });

      await renderPage({ country: "DE" }, makeViewer());

      expect(
        screen.queryByRole("columnheader", { name: "Lowest to highest" }),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByRole("region", { name: /Who earns the most/ }),
      ).not.toBeInTheDocument();
    });
  });

  it("shows pay by department in US$ across countries, saying so", async () => {
    serveInsights();

    await renderPage();

    const departments = section("How does pay differ between departments?");
    expect(
      within(departments).getByRole("row", { name: /Engineering/ }),
    ).toHaveTextContent("US$98,000");
    expect(departments).toHaveTextContent(
      "In US$ at exchange rates of 1 Oct 2026",
    );
  });

  it("shows where the payroll goes, with each department's share", async () => {
    serveInsights();

    await renderPage();

    const cost = section("Where does the payroll go?");
    const engineering = within(cost).getByRole("listitem", {
      name: /Engineering/,
    });
    expect(engineering).toHaveTextContent("US$362.3M");
    expect(engineering).toHaveTextContent("44%");
  });

  it("asks for a country before comparing job titles", async () => {
    // No by-job-title handler: asking for it without a country would fail the test.
    serveInsights();

    await renderPage();

    expect(section("What does each job pay?")).toHaveTextContent(
      "Choose a country",
    );
  });

  it("compares job titles within the chosen country, by level when asked", async () => {
    const seen = serveInsights({
      byJobTitle: makeByJobTitle({
        split_by_level: true,
        groups: [
          {
            job_role: { id: 17, title: "Customer Success Manager" },
            level: "L2",
            stats: makeStats({ count: 18, median: 4_700_000 }),
          },
        ],
      }),
      topEarners: makeTopEarners(),
    });

    await renderPage({ country: "DE", split_by_level: "true" });

    const [query] = seen.get("/api/v1/insights/by-job-title") ?? [];
    expect(query?.get("split_by_level")).toBe("true");
    const jobs = section("What does each job pay in Germany?");
    expect(
      within(jobs).getByRole("row", { name: /Customer Success Manager, L2/ }),
    ).toHaveTextContent("€47,000");
  });

  it("lists the top earners of a country for HR, linked to each employee", async () => {
    const seen = serveInsights({
      byJobTitle: makeByJobTitle(),
      topEarners: makeTopEarners(),
    });

    await renderPage({ country: "DE" });

    const [query] = seen.get("/api/v1/insights/top-earners") ?? [];
    expect(query?.get("direction")).toBe("top");
    const top = section("Who earns the most in Germany?");
    expect(
      within(top).getByRole("link", { name: "Katharina Vogel" }),
    ).toHaveAttribute("href", "/employees/2210");
    expect(top).toHaveTextContent("€168,000");
  });

  it("lists the lowest earners when the URL asks for the bottom", async () => {
    const seen = serveInsights({
      byJobTitle: makeByJobTitle(),
      topEarners: makeTopEarners({ direction: "bottom" }),
    });

    await renderPage({ country: "DE", direction: "bottom" });

    const [query] = seen.get("/api/v1/insights/top-earners") ?? [];
    expect(query?.get("direction")).toBe("bottom");
    expect(section("Who earns the least in Germany?")).toBeVisible();
  });

  it("shows a failed insight as a problem with its request id, and the rest of the page", async () => {
    serveInsights();
    server.use(
      http.get<never, never, S["Problem"]>(
        `${API_ORIGIN}/api/v1/insights/department-cost`,
        () =>
          HttpResponse.json(
            makeProblem("internal", 503, {
              title: "Service unavailable",
              detail: "The database is busy. Try again in a moment.",
              request_id: "req-503",
            }),
            { status: 503 },
          ),
      ),
    );

    await renderPage();

    const cost = section("Where does the payroll go?");
    expect(within(cost).getByRole("alert")).toHaveTextContent(
      "Request ID: req-503",
    );
    expect(section(COUNTRY_QUESTION)).toBeVisible();
  });

  it("says so when nobody matches the filters", async () => {
    serveInsights({
      overview: makeOverview({
        headcount: 0,
        total_payroll_usd: { amount_minor: 0, currency: "USD" },
        by_country: [],
      }),
      byDepartment: makeByDepartment({ groups: [] }),
      departmentCost: makeDepartmentCosts({ groups: [] }),
    });

    await renderPage({ status: "TERMINATED" });

    expect(screen.getByText("Nobody matches these filters")).toBeVisible();
  });
});
