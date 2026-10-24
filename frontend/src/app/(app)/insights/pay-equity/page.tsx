import type { Metadata } from "next";
import Link from "next/link";

import { InsightsBusy } from "@/components/insights/insights-controls";
import { InsightsProvider } from "@/components/insights/insights-state";
import { countryName } from "@/components/insights/overview";
import { settle, type Result } from "@/components/insights/result";
import { CohortList } from "@/components/pay-equity/cohort-list";
import { PayEquityFilters } from "@/components/pay-equity/pay-equity-filters";
import { TeamView } from "@/components/pay-equity/team-view";
import { EmptyState, ErrorState, PageTitle, Section } from "@/components/print";
import { ProblemError } from "@/lib/api/problem";
import { getReference } from "@/lib/api/reference";
import type { components } from "@/lib/api/schema";
import { serverApi } from "@/lib/api/server";
import { loadPayEquityParams, serializePayEquity } from "@/lib/insights-params";
import { formatCount } from "@/lib/numbers";

type S = components["schemas"];

export const metadata: Metadata = { title: "Pay equity" };

const COHORTS_QUESTION = "Which roles and levels?";

/**
 * Pay equity (docs/13-frontend-ux.md §4.3): one country's teams and cohorts against their
 * pay bands, from GET /insights/pay-equity (both views at once). Every ratio, count, flag
 * and hidden group comes from the API; the drill-down to people needs SALARY_READ.
 */
export default async function PayEquityPage({
  searchParams,
}: PageProps<"/insights/pay-equity">) {
  const state = await loadPayEquityParams(searchParams);
  let reference;
  try {
    reference = await getReference();
  } catch (error) {
    if (error instanceof ProblemError) {
      return (
        <>
          <PageTitle title="Are we paying people fairly?" />
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

  const country = state.country;
  if (!country) return <ChooseCountry reference={reference} />;

  const name = countryName(country, reference);
  const api = await serverApi();
  const query = {
    country: [country],
    ...(state.department_id !== null
      ? { department_id: [state.department_id] }
      : {}),
  };
  const [departments, cohorts] = await Promise.all([
    settle(
      api.GET("/api/v1/insights/pay-equity", {
        params: { query: { ...query, view: "departments" } },
      }),
    ),
    settle(
      api.GET("/api/v1/insights/pay-equity", {
        params: { query: { ...query, view: "cohorts" } },
      }),
    ),
  ]);
  const teams = asView(departments, "departments");
  const cohortResult = asView(cohorts, "cohorts");
  const summary = cohortResult.data?.summary ?? teams.data?.summary ?? null;

  return (
    <InsightsProvider>
      <Link
        href={`/insights?country=${encodeURIComponent(country)}`}
        className="inline-flex min-h-11 items-center"
      >
        Back to insights
      </Link>
      <PageTitle
        title={`Are we paying ${name} fairly?`}
        actions={<PayEquityFilters reference={reference} />}
      >
        {summary ? <SummarySentence summary={summary} name={name} /> : null}
      </PageTitle>
      <Explainer />
      <InsightsBusy>
        <TeamView result={teams} />
        <Section question={COHORTS_QUESTION}>
          {cohortResult.data ? (
            cohortResult.data.cohorts.length === 0 ? (
              <EmptyState title="No roles to compare">
                Nobody here has a pay band to compare with.
              </EmptyState>
            ) : (
              <CohortList
                cohorts={cohortResult.data.cohorts}
                countryName={name}
              />
            )
          ) : (
            <ErrorState {...cohortResult.problem} />
          )}
        </Section>
      </InsightsBusy>
    </InsightsProvider>
  );
}

type Views = S["PayEquityCohorts"] | S["PayEquityDepartments"];

/** One view's result, typed as that view (the endpoint answers with either shape). */
function asView<V extends Views["view"]>(
  result: Result<Views>,
  view: V,
): Result<Extract<Views, { view: V }>> {
  if (!result.data) return result;
  if (result.data.view === view) {
    return { data: result.data as Extract<Views, { view: V }>, problem: null };
  }
  return {
    data: null,
    problem: {
      title: "Something went wrong",
      detail: "The API sent an answer this page doesn't understand.",
      requestId: null,
    },
  };
}

/** Who was compared, who was left out and why, and how many are flagged. */
function SummarySentence({
  summary,
  name,
}: {
  summary: S["PayEquitySummary"];
  name: string;
}) {
  const {
    employees_evaluated: evaluated,
    employees_flagged_underpaid: under,
    employees_flagged_overpaid: over,
    employees_not_full_time: notFullTime,
    employees_without_band: withoutBand,
  } = summary;
  if (
    summary.suppressed ||
    evaluated === null ||
    under === null ||
    over === null ||
    notFullTime === null ||
    withoutBand === null
  ) {
    return <>Too few people match to show their pay equity (fewer than 5).</>;
  }
  return (
    <>
      {formatCount(evaluated)} full-time employees in {name} were compared with
      their pay bands: {formatCount(under)} are paid below their band and{" "}
      {formatCount(over)} above it. {formatCount(notFullTime)} who aren&apos;t
      full-time are left out, and {formatCount(withoutBand)} have no band.
    </>
  );
}

function Explainer() {
  return (
    <details className="mt-4 max-w-[760px] text-[15px] text-ink-2">
      <summary className="inline-flex min-h-11 cursor-pointer items-center font-bold text-ink">
        What is a compa-ratio?
      </summary>
      <p className="pb-2">
        Compa-ratio = base pay ÷ the midpoint of the pay band for the same role,
        level and country. 1.00 is the middle of the band; below 0.80 is under
        the band minimum (may be underpaid); above 1.20 is over the band
        maximum. Pay bands are defined on base salary, so total pay and
        part-time pay aren&apos;t compared.
      </p>
    </details>
  );
}

function ChooseCountry({ reference }: { reference: S["ReferenceData"] }) {
  return (
    <InsightsProvider>
      <PageTitle
        title="Are we paying people fairly?"
        actions={<PayEquityFilters reference={reference} />}
      >
        We compare each person&apos;s base pay with the middle of the pay band
        for their role, level and country. Bands differ by country, so choose
        one.
      </PageTitle>
      <Explainer />
      <Section question="Which country?">
        <ul className="flex flex-wrap gap-x-6">
          {reference.countries
            .filter((country) => country.is_active)
            .map((country) => (
              <li key={country.code}>
                <Link
                  href={`/insights/pay-equity${serializePayEquity({
                    country: country.code,
                    department_id: null,
                  })}`}
                  className="inline-flex min-h-11 items-center text-base"
                >
                  {country.name}
                </Link>
              </li>
            ))}
        </ul>
      </Section>
    </InsightsProvider>
  );
}
