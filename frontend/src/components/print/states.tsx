import Link from "next/link";
import type { ReactNode } from "react";

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
export function Forbidden() {
  return (
    <div className="border-t-2 border-ink py-10">
      <h1 className="font-serif text-[32px] leading-[1.1] font-semibold sm:text-[44px]">
        You don&apos;t have access to this
      </h1>
      <p className="mt-3 max-w-[640px] text-[17px] text-ink-2">
        Your role doesn&apos;t include this page.
      </p>
      <Link
        href="/insights"
        className="mt-4 inline-flex min-h-11 items-center text-base font-bold"
      >
        Go to Insights
      </Link>
    </div>
  );
}
