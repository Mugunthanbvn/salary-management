import type { Metadata } from "next";

import { Forbidden, PageTitle } from "@/components/print";
import { getMe } from "@/lib/api/me";
import { can } from "@/lib/permissions";

export const metadata: Metadata = { title: "Import employees" };

// Placeholder until the import screen is built (docs/13-frontend-ux.md §4.7).
export default async function ImportPage() {
  const me = await getMe();
  if (!can(me, "IMPORT")) return <Forbidden />;
  return (
    <PageTitle title="Import employees">
      Upload a CSV or Excel file of new hires, check it, then add them all at
      once.
    </PageTitle>
  );
}
