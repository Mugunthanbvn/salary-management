import type { Metadata } from "next";

import { Forbidden, PageTitle } from "@/components/print";
import { getMe } from "@/lib/api/me";
import { can } from "@/lib/permissions";

export const metadata: Metadata = { title: "Ask about pay" };

// Placeholder until Ask is built (docs/13-frontend-ux.md §4.8).
export default async function AskPage() {
  const me = await getMe();
  if (!me.features.ask) {
    return <Forbidden reason="Ask is switched off on this deployment." />;
  }
  if (!can(me, "ASK")) return <Forbidden />;
  return (
    <PageTitle title="Ask about pay">
      Ask a question about how ACME pays people, in plain words.
    </PageTitle>
  );
}
