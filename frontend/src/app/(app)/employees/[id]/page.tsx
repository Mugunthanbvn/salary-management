import type { Metadata } from "next";

import { PageTitle } from "@/components/print";

export const metadata: Metadata = { title: "Employee" };

// Placeholder until the detail page is built (docs/13-frontend-ux.md §4.5).
export default function EmployeePage() {
  return (
    <PageTitle title="Employee">
      Their details, current pay and salary history.
    </PageTitle>
  );
}
