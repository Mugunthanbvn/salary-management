import type { Metadata } from "next";
import Link from "next/link";

import {
  DepartmentCost,
  DepartmentPay,
} from "@/components/insights/departments";
import {
  InsightsBusy,
  InsightsControls,
  PayToggles,
} from "@/components/insights/insights-controls";
import { InsightsProvider } from "@/components/insights/insights-state";
import { JobTitlePay, TopEarners } from "@/components/insights/jobs";
import {
  CountryPay,
  countryName,
  OverviewSentence,
} from "@/components/insights/overview";
import { settle } from "@/components/insights/result";
import { EmptyState, ErrorState, PageTitle } from "@/components/print";
import { getMe } from "@/lib/api/me";
import { ProblemError } from "@/lib/api/problem";
import { getReference } from "@/lib/api/reference";
import { serverApi } from "@/lib/api/server";
import {
  loadInsightsParams,
  serializePayEquity,
  toInsightQuery,
} from "@/lib/insights-params";
import { can, canAsk } from "@/lib/permissions";

export const metadata: Metadata = { title: "Insights" };

const TITLE = "How ACME pays people";
const TOP_EARNERS = 10;

/**
 * The insights dashboard (docs/13-frontend-ux.md §4.2). The URL holds the filters and
 * toggles; this Server Component asks each insight endpoint for them at once and renders
 * the answers. Every figure, currency and hidden group comes from the API. The (app)
 * loading.tsx is its Suspense boundary.
 */
export default async function InsightsPage({
  searchParams,
}: PageProps<"/insights">) {
  const [me, state] = await Promise.all([
    getMe(),
    loadInsightsParams(searchParams),
  ]);
  let reference;
  try {
    reference = await getReference();
  } catch (error) {
    if (error instanceof ProblemError) {
      return (
        <>
          <PageTitle title={TITLE} />
          <div className="mt-8">
            <ErrorState
              title={error.title}
              detail={error.detail}
              requestId={error.requestId}
            />
          </div>
        </>
      );
    }
    throw error;
  }

  const api = await serverApi();
  const query = toInsightQuery(state);
  const country = state.country;
  // Individuals' pay: asked for only by people who may see it, for one country.
  const showEarners = can(me, "SALARY_READ");
  const [overview, byDepartment, cost, jobs, earners] = await Promise.all([
    settle(api.GET("/api/v1/insights/overview", { params: { query } })),
    settle(api.GET("/api/v1/insights/by-department", { params: { query } })),
    settle(api.GET("/api/v1/insights/department-cost", { params: { query } })),
    country
      ? settle(
          api.GET("/api/v1/insights/by-job-title", {
            params: {
              query: {
                ...query,
                country,
                split_by_level: state.split_by_level,
              },
            },
          }),
        )
      : null,
    showEarners && country
      ? settle(
          api.GET("/api/v1/insights/top-earners", {
            params: {
              query: {
                ...query,
                country,
                direction: state.direction,
                n: TOP_EARNERS,
              },
            },
          }),
        )
      : null,
  ]);
  const name = country ? countryName(country, reference) : null;
  const nobody = overview.data?.headcount === 0;

  return (
    <InsightsProvider>
      <PageTitle title={TITLE} actions={<PayToggles />}>
        {overview.data ? (
          <OverviewSentence overview={overview.data} state={state} />
        ) : null}
      </PageTitle>
      <InsightsControls reference={reference} />
      <InsightsBusy>
        {nobody ? (
          <EmptyState
            title="Nobody matches these filters"
            action={
              <Link
                href="/insights"
                className="inline-flex min-h-11 items-center font-bold"
              >
                Show full-time, active employees
              </Link>
            }
          >
            Try another country or department, or count more kinds of employees.
          </EmptyState>
        ) : (
          <div className="mt-2">
            <CountryPay result={overview} state={state} reference={reference} />
            <DepartmentPay result={byDepartment} />
            <DepartmentCost result={cost} />
            <JobTitlePay result={jobs} countryName={name} />
            {showEarners ? (
              <TopEarners
                result={earners}
                direction={state.direction}
                countryName={name}
              />
            ) : null}
          </div>
        )}
      </InsightsBusy>
      <nav
        aria-label="More about pay"
        className="flex flex-wrap gap-x-8 border-t-2 border-ink pt-4"
      >
        <Link
          href={`/insights/pay-equity${serializePayEquity({
            country,
            department_id: state.department_id,
          })}`}
          className="inline-flex min-h-11 items-center font-bold"
        >
          Open pay equity{name ? ` for ${name}` : ""}
        </Link>
        {canAsk(me) ? (
          <Link
            href="/ask"
            className="inline-flex min-h-11 items-center font-bold"
          >
            Ask a question about pay
          </Link>
        ) : null}
      </nav>
    </InsightsProvider>
  );
}
