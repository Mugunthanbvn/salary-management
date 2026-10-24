import type { Metadata } from "next";

import { PageTitle } from "@/components/print";

export const metadata: Metadata = { title: "Pay equity" };

// Placeholder until pay equity is built (docs/13-frontend-ux.md §4.3).
export default async function PayEquityPage({
  searchParams,
}: PageProps<"/insights/pay-equity">) {
  await searchParams;
  return (
    <PageTitle title="Is anyone paid unfairly?">
      How each team&apos;s pay compares with its pay bands.
    </PageTitle>
  );
}
