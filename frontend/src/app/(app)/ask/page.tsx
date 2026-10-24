import type { Metadata, Viewport } from "next";

import { Forbidden, PageTitle } from "@/components/print";
import { getMe } from "@/lib/api/me";
import { can } from "@/lib/permissions";

import { AskChat } from "./ask-chat";

export const metadata: Metadata = { title: "Ask about pay" };

// Phones: the on-screen keyboard shrinks the layout, so the sticky question box stays above it.
export const viewport: Viewport = { interactiveWidget: "resizes-content" };

/** Ask about pay (docs/13-frontend-ux.md §4.8). The API still decides every answer. */
export default async function AskPage() {
  const me = await getMe();
  if (!me.features.ask) {
    return <Forbidden reason="Ask is turned off on this deployment." />;
  }
  if (!can(me, "ASK")) return <Forbidden />;
  return (
    <div className="mx-auto max-w-[880px]">
      <PageTitle title="Ask about pay">
        Ask about how ACME pays people. Answers use the same numbers as the
        dashboard and show how they were worked out.
      </PageTitle>
      <AskChat />
    </div>
  );
}
