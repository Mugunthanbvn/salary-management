import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import type { ReactNode } from "react";

import { Compensation } from "@/components/employees/compensation";
import { EmployeeActions } from "@/components/employees/employee-actions";
import { countryName, fullName } from "@/components/employees/format";
import { SalaryTimeline } from "@/components/employees/salary-timeline";
import { ErrorState, PageTitle, Section, StatusWord } from "@/components/print";
import { getMe } from "@/lib/api/me";
import { ProblemError, toProblem } from "@/lib/api/problem";
import { getReference } from "@/lib/api/reference";
import type { components } from "@/lib/api/schema";
import { serverApi } from "@/lib/api/server";
import { formatDate } from "@/lib/dates";
import { EMPLOYMENT_TYPE_LABELS, STATUS_LABELS } from "@/lib/labels";
import { can } from "@/lib/permissions";

type EmployeeDetail = components["schemas"]["EmployeeDetail"];
type ReferenceData = components["schemas"]["ReferenceData"];

export const metadata: Metadata = { title: "Employee" };

/** Ids are positive integers; anything else (or too large to be one) is a 404. */
function employeeIdFrom(segment: string): number | null {
  return /^[1-9]\d{0,14}$/.test(segment) ? Number(segment) : null;
}

/**
 * An employee's page (docs/13-frontend-ux.md §4.5): who they are, what they are paid and how
 * their pay got there. Pay and history need SALARY_READ: for anyone else the API masks pay,
 * the history is not even asked for, and a neutral note takes their place.
 * The (app) loading.tsx and this route's loading.tsx are its Suspense boundary.
 */
export default async function EmployeePage({
  params,
}: PageProps<"/employees/[id]">) {
  const employeeId = employeeIdFrom((await params).id);
  if (employeeId === null) notFound();
  const me = await getMe();
  const canReadSalaries = can(me, "SALARY_READ");
  const api = await serverApi();
  const path = { employee_id: employeeId };
  const [employee, reference, history] = await Promise.all([
    api.GET("/api/v1/employees/{employee_id}", { params: { path } }),
    getReference().catch((error: unknown) => error),
    canReadSalaries
      ? api.GET("/api/v1/employees/{employee_id}/salary-history", {
          params: { path },
        })
      : null,
  ]);

  if (!employee.data) {
    // 422: an id the API can't hold (beyond 64 bits) is no employee either.
    if (employee.response.status === 404 || employee.response.status === 422) {
      notFound();
    }
    const problem = await toProblem(employee.response, employee.error);
    return <PageProblem problem={problem} />;
  }
  if (reference instanceof ProblemError)
    return <PageProblem problem={reference} />;
  if (reference instanceof Error) throw reference;
  const data = employee.data;
  const name = data.first_name;
  const ref = reference as ReferenceData;
  const showsPhoneBar =
    can(me, "SALARY_WRITE") &&
    data.status === "ACTIVE" &&
    data.version !== null;
  const historyProblem =
    history && !history.data
      ? await toProblem(history.response, history.error)
      : null;

  return (
    <>
      <Link
        href="/employees"
        className="-mt-2 mb-2 inline-flex min-h-11 items-center text-[15px] sm:-mt-6"
      >
        Back to employees
      </Link>
      <PageTitle
        title={fullName(data)}
        actions={<EmployeeActions employee={data} reference={ref} />}
      >
        {summary(data, ref)}
        {data.status === "TERMINATED" ? (
          <>
            {" "}
            <StatusWord tone="plain">
              <strong>
                Terminated
                {data.termination_date
                  ? ` on ${formatDate(data.termination_date)}`
                  : ""}
                .
              </strong>
            </StatusWord>
          </>
        ) : null}
      </PageTitle>

      <Section question={`What is ${name} paid?`}>
        {data.salary_masked ? (
          <p className="text-[17px] text-ink-2">
            Compensation details are restricted for your role.
          </p>
        ) : (
          <Compensation employee={data} />
        )}
      </Section>

      {history ? (
        <Section question={`How did ${possessive(name)} pay get here?`}>
          {history.data ? (
            <SalaryTimeline records={history.data.records} />
          ) : historyProblem ? (
            <ErrorState
              title={historyProblem.title}
              detail={
                historyProblem.detail ?? "The salary history couldn't load."
              }
              requestId={historyProblem.requestId}
            />
          ) : null}
        </Section>
      ) : null}

      <Section question={`Who is ${name}?`}>
        <Profile employee={data} reference={ref} />
      </Section>

      {/* Room for the phone action bar, so it never covers the end of the page. */}
      {showsPhoneBar ? (
        <div aria-hidden="true" className="h-20 sm:hidden" />
      ) : null}
    </>
  );
}

/** "Customer Success Manager, L2, in Customer Success, Germany. Full-time since 1 Jun 2022. ACME-002210." */
function summary(employee: EmployeeDetail, reference: ReferenceData): string {
  return (
    `${employee.job_role.title}, ${employee.level}, in ${employee.department.name}, ` +
    `${countryName(employee.country_code, reference)}. ` +
    `${EMPLOYMENT_TYPE_LABELS[employee.employment_type]} since ${formatDate(employee.hire_date)}. ` +
    `${employee.employee_code}.`
  );
}

/** "Lena's", "James's". */
function possessive(name: string): string {
  return `${name}'s`;
}

function Profile({
  employee,
  reference,
}: {
  employee: EmployeeDetail;
  reference: ReferenceData;
}) {
  const level = reference.levels.find((l) => l.code === employee.level);
  const rows: [string, ReactNode][] = [
    ["Email", employee.email],
    ["Employee code", employee.employee_code],
    ["Job role", employee.job_role.title],
    ["Level", level ? `${level.code} ${level.label}` : employee.level],
    ["Department", employee.department.name],
    ["Country", countryName(employee.country_code, reference)],
    ["Employment type", EMPLOYMENT_TYPE_LABELS[employee.employment_type]],
    ["Status", STATUS_LABELS[employee.status]],
    ["Hired", formatDate(employee.hire_date)],
  ];
  if (employee.termination_date) {
    rows.push(["Terminated", formatDate(employee.termination_date)]);
  }
  return (
    <dl className="grid max-w-[640px] grid-cols-1 text-base sm:grid-cols-[200px_minmax(0,1fr)]">
      {rows.map(([label, value]) => (
        <div key={label} className="contents">
          <dt className="pt-2.5 text-sm text-ink-2 sm:border-t sm:border-rule sm:py-2.5 sm:text-base sm:text-ink">
            {label}
          </dt>
          <dd className="border-b border-rule pb-2.5 break-words sm:border-t sm:border-b-0 sm:py-2.5">
            {value}
          </dd>
        </div>
      ))}
    </dl>
  );
}

function PageProblem({ problem }: { problem: ProblemError }) {
  return (
    <>
      <Link
        href="/employees"
        className="mb-2 inline-flex min-h-11 items-center"
      >
        Back to employees
      </Link>
      <ErrorState
        title={problem.title}
        detail={problem.detail}
        requestId={problem.requestId}
      />
    </>
  );
}
