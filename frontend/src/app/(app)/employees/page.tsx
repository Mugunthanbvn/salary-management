import type { Metadata } from "next";

import { PageTitle } from "@/components/print";

export const metadata: Metadata = { title: "Employees" };

// Placeholder until the directory is built (docs/13-frontend-ux.md §4.4).
export default async function EmployeesPage({
  searchParams,
}: PageProps<"/employees">) {
  await searchParams;
  return (
    <PageTitle title="Who are you looking for?">
      Find an employee by name, employee code or email.
    </PageTitle>
  );
}
