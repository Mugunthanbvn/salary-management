import { Skeleton } from "@/components/ui/skeleton";

/**
 * A dashboard's shape while it loads: the title block with its toggles, the filter row,
 * then `sections` question-and-answer rows of table lines (docs/13-frontend-ux.md §3.1).
 */
export function DashboardSkeleton({ sections }: { sections: number }) {
  return (
    <div aria-busy="true">
      <p className="sr-only" role="status">
        Loading…
      </p>
      <div className="flex flex-wrap items-end justify-between gap-6 border-b-2 border-ink pb-6 sm:pb-8">
        <div className="min-w-0 flex-[999_1_560px]">
          <Skeleton className="h-9 w-3/4 max-w-[520px] sm:h-12" />
          <Skeleton className="mt-4 h-5 w-full max-w-[640px]" />
        </div>
        <Skeleton className="h-11 w-full sm:w-72" />
      </div>
      <div className="mt-6 flex flex-wrap gap-4">
        <Skeleton className="h-11 w-48" />
        <Skeleton className="h-11 w-56" />
      </div>
      {Array.from({ length: sections }, (_, row) => (
        <div
          key={row}
          data-skeleton-section
          className="flex flex-wrap gap-x-12 gap-y-4 border-b border-rule py-8 sm:py-10"
        >
          <Skeleton className="h-8 flex-[1_1_280px]" />
          <div className="flex flex-[999_1_640px] flex-col gap-3">
            {[0, 1, 2, 3, 4].map((line) => (
              <Skeleton key={line} className="h-11 w-full" />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
