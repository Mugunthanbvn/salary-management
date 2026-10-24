import type { Metadata } from "next";

import { PageTitle } from "@/components/print";

export const metadata: Metadata = { title: "Insights" };

// Placeholder until the dashboard is built (docs/13-frontend-ux.md §4.2).
export default function InsightsPage() {
  return (
    <PageTitle title="How ACME pays people">
      Pay by country, team and role, in each country&apos;s own currency.
    </PageTitle>
  );
}
