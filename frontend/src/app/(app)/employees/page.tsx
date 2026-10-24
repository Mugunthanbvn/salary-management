import type { Metadata } from "next";
import Link from "next/link";

import { DirectoryProvider } from "@/components/employees/directory-state";
import { DirectoryToolbar } from "@/components/employees/directory-toolbar";
import { EmployeeResults } from "@/components/employees/employee-results";
import { ExportMenu } from "@/components/employees/export-menu";
import { ErrorState, PageTitle } from "@/components/print";
import { buttonVariants } from "@/components/ui/button";
import { getMe } from "@/lib/api/me";
import { ProblemError, toProblem } from "@/lib/api/problem";
import { getReference } from "@/lib/api/reference";
import type { components } from "@/lib/api/schema";
import { serverApi } from "@/lib/api/server";
import {
  hasFilters,
  loadDirectoryParams,
  toListQuery,
} from "@/lib/directory-params";
import { formatCount } from "@/lib/numbers";
import { can, type Me } from "@/lib/permissions";

export const metadata: Metadata = { title: "Employees" };

const TITLE = "Who are you looking for?";

/**
 * The employee directory (docs/13-frontend-ux.md §4.4). The URL holds the filters, sort and
 * page; this Server Component turns them into GET /employees (only what the API accepts
 * from this person) and renders the answer. The (app) loading.tsx is its Suspense boundary.
 */
export default async function EmployeesPage({
  searchParams,
}: PageProps<"/employees">) {
  const [me, state] = await Promise.all([
    getMe(),
    loadDirectoryParams(searchParams),
  ]);
  let reference;
  try {
    reference = await getReference();
  } catch (error) {
    if (error instanceof ProblemError)
      return <Problem me={me} problem={error} />;
    throw error;
  }

  const api = await serverApi();
  const { data, error, response } = await api.GET("/api/v1/employees", {
    params: {
      query: toListQuery(state, {
        canReadSalaries: can(me, "SALARY_READ"),
        reference,
      }),
    },
  });
  const problem = data ? null : await toProblem(response, error);

  return (
    <>
      <PageTitle
        title={TITLE}
        actions={<Actions me={me} reference={reference} />}
      >
        {data ? countSentence(data.total, hasFilters(state)) : null}
      </PageTitle>
      <DirectoryProvider>
        <DirectoryToolbar reference={reference} total={data?.total ?? 0} />
        {data ? (
          <EmployeeResults page={data} reference={reference} />
        ) : problem ? (
          <div className="mt-8">
            <ErrorState
              title={problem.title}
              detail={problem.detail}
              requestId={problem.requestId}
            />
          </div>
        ) : null}
      </DirectoryProvider>
    </>
  );
}

/** "9,412 active employees." or, once anything is filtered, "37 employees match." */
function countSentence(total: number, filtered: boolean): string {
  const count = formatCount(total);
  if (filtered)
    return `${count} ${total === 1 ? "employee matches" : "employees match"}.`;
  return `${count} active ${total === 1 ? "employee" : "employees"}.`;
}

/**
 * Add needs both write permissions: a new hire comes with their first salary. Export needs
 * the reference data to send only the filters the API accepts, so it waits for it.
 */
function Actions({
  me,
  reference,
}: {
  me: Me;
  reference?: components["schemas"]["ReferenceData"];
}) {
  const canAdd = can(me, "EMPLOYEE_WRITE") && can(me, "SALARY_WRITE");
  const canImport = can(me, "IMPORT");
  const canExport = can(me, "EXPORT") && reference !== undefined;
  if (!canAdd && !canImport && !canExport) return null;
  return (
    <>
      {canExport ? <ExportMenu reference={reference} /> : null}
      {canImport ? (
        <Link
          href="/employees/import"
          className={buttonVariants({
            variant: "secondary",
            className: "font-normal no-underline hover:text-ink",
          })}
        >
          Import from Excel
        </Link>
      ) : null}
      {canAdd ? (
        <Link
          href="/employees/new"
          className={buttonVariants({
            className: "no-underline hover:text-paper",
          })}
        >
          Add employee
        </Link>
      ) : null}
    </>
  );
}

function Problem({ me, problem }: { me: Me; problem: ProblemError }) {
  return (
    <>
      <PageTitle title={TITLE} actions={<Actions me={me} />} />
      <div className="mt-8">
        <ErrorState
          title={problem.title}
          detail={problem.detail}
          requestId={problem.requestId}
        />
      </div>
    </>
  );
}
