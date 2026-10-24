"use client";

import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";

type ErrorStateProps = {
  /** The problem's `title`, e.g. "Service unavailable". */
  title: string;
  /** The problem's `detail`, in plain language. */
  detail?: string | null;
  /** The problem's `request_id`, so support can find it in the API logs. */
  requestId?: string | null;
  /** How to try again; without it, the page's server data is fetched again. */
  onRetry?: () => void;
};

/**
 * Shown when the API answered with a problem (docs/13-frontend-ux.md §3.6). Pass plain
 * fields, not a ProblemError: a Server Component can render it with the problem's values.
 */
export function ErrorState({
  title,
  detail,
  requestId,
  onRetry,
}: ErrorStateProps) {
  const router = useRouter();
  return (
    <div role="alert" className="border-t-2 border-red-pen py-8">
      <p className="font-serif text-[22px] leading-tight font-semibold">
        {title}
      </p>
      {detail ? (
        <p className="mt-2 max-w-[640px] text-[15px] text-ink">{detail}</p>
      ) : null}
      {requestId ? (
        <p className="mt-2 text-sm text-ink-3">Request ID: {requestId}</p>
      ) : null}
      <Button
        variant="secondary"
        className="mt-4"
        onClick={() => (onRetry ? onRetry() : router.refresh())}
      >
        Try again
      </Button>
    </div>
  );
}
