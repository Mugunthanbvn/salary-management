import type { Metadata } from "next";

import { Forbidden, PageTitle } from "@/components/print";
import { getMe } from "@/lib/api/me";
import { can } from "@/lib/permissions";

export const metadata: Metadata = { title: "Add an employee" };

// Placeholder until the create form is built (docs/13-frontend-ux.md §4.6).
export default async function NewEmployeePage() {
  const me = await getMe();
  if (!can(me, "EMPLOYEE_WRITE")) return <Forbidden />;
  return (
    <PageTitle title="Add an employee">
      Enter a new hire&apos;s details and starting salary.
    </PageTitle>
  );
}
