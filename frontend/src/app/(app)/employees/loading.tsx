import { Skeleton } from "@/components/ui/skeleton";

const ROWS = Array.from({ length: 8 }, (_, index) => index);

/**
 * The directory's shape while it loads (docs/13-frontend-ux.md §3.1): title, search,
 * filters and rows, as a table from 640 px and a list below, so nothing jumps.
 */
export default function DirectoryLoading() {
  return (
    <div aria-busy="true">
      <p className="sr-only" role="status">
        Loading employees…
      </p>
      <div className="border-b-2 border-ink pb-6 sm:pb-8">
        <Skeleton className="h-9 w-3/4 max-w-[520px] sm:h-12" />
        <Skeleton className="mt-4 h-5 w-48" />
      </div>
      <Skeleton className="mt-8 h-4 w-64 sm:mt-10" />
      <div className="mt-2 h-12 border-b-2 border-ink sm:h-16" />
      <div className="mt-5 flex flex-wrap gap-2.5">
        {[0, 1, 2, 3].map((chip) => (
          <Skeleton key={chip} className="h-11 w-32" />
        ))}
      </div>
      <div data-slot="rows-table" className="mt-10 hidden sm:block">
        <div className="border-b-2 border-ink pb-2.5">
          <Skeleton className="h-4 w-1/2" />
        </div>
        {ROWS.map((row) => (
          <div key={row} className="flex gap-6 border-b border-rule py-4">
            <Skeleton className="h-5 w-40" />
            <Skeleton className="h-5 flex-1" />
            <Skeleton className="h-5 w-24" />
            <Skeleton className="h-5 w-28" />
          </div>
        ))}
      </div>
      <div data-slot="rows-list" className="mt-6 sm:hidden">
        {ROWS.map((row) => (
          <div
            key={row}
            className="flex justify-between gap-3 border-t border-rule py-3.5"
          >
            <div className="flex flex-1 flex-col gap-2">
              <Skeleton className="h-5 w-2/3" />
              <Skeleton className="h-4 w-1/2" />
            </div>
            <Skeleton className="h-6 w-24" />
          </div>
        ))}
      </div>
    </div>
  );
}
