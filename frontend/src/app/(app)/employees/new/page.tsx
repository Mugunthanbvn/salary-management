import type { Metadata } from "next";

import { NewEmployeeForm } from "@/components/employees/new-employee-form";
import { ErrorState, Forbidden, PageTitle } from "@/components/print";
import { getMe } from "@/lib/api/me";
import { ProblemError } from "@/lib/api/problem";
import { getReference } from "@/lib/api/reference";
import { can } from "@/lib/permissions";

export const metadata: Metadata = { title: "Add an employee" };

/**
 * Add an employee (docs/13-frontend-ux.md §4.6). A new hire comes with their first salary,
 * so it needs EMPLOYEE_WRITE and SALARY_WRITE, like POST /employees.
 */
export default async function NewEmployeePage() {
  const me = await getMe();
  if (!can(me, "EMPLOYEE_WRITE") || !can(me, "SALARY_WRITE")) {
    return <Forbidden />;
  }
  let reference;
  try {
    reference = await getReference();
  } catch (error) {
    if (!(error instanceof ProblemError)) throw error;
    return (
      <ErrorState
        title={error.title}
        detail={error.detail}
        requestId={error.requestId}
      />
    );
  }
  return (
    <>
      <PageTitle title="Add an employee">
        Enter a new hire&apos;s details and starting salary.
      </PageTitle>
      <NewEmployeeForm reference={reference} />
    </>
  );
}
