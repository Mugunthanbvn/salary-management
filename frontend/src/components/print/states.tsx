import Link from "next/link";
import type { ReactNode } from "react";

import { PageTitle } from "./page-title";

type EmptyStateProps = {
  /** What is missing, plainly: "No employees match these filters". */
  title: string;
  /** Why, or what to try. */
  children?: ReactNode;
  /** The next step, e.g. a "Clear filters" button or a link. */
  action?: ReactNode;
};

/** Shown in place of a list, table or answer that has nothing in it. */
export function EmptyState({ title, children, action }: EmptyStateProps) {
  return (
    <div className="py-10">
      <p className="font-serif text-[22px] leading-tight font-semibold">
        {title}
      </p>
      {children ? (
        <p className="mt-2 max-w-[640px] text-[15px] text-ink-2">{children}</p>
      ) : null}
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}

/**
 * The page for a route this person's permissions don't allow (never a blank page). The
 * UI only hides; FastAPI still refuses the API calls with 403.
 */
export function Forbidden({
  reason = "Your role doesn't include this page.",
}: {
  reason?: string;
}) {
  return (
    <>
      <PageTitle title="You don't have access to this">{reason}</PageTitle>
      <Link
        href="/insights"
        className="mt-6 inline-flex min-h-11 items-center text-base font-bold"
      >
        Go to Insights
      </Link>
    </>
  );
}
