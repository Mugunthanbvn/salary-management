import { Skeleton } from "@/components/ui/skeleton";

import { BrandBar } from "./brand-bar";

/**
 * The page's shape while it loads: a title block over two question-and-answer sections,
 * so nothing jumps when the content arrives (docs/13-frontend-ux.md §3.1).
 */
export function PageSkeleton() {
  return (
    <div aria-busy="true">
      <p className="sr-only" role="status">
        Loading…
      </p>
      <div className="border-b-2 border-ink pb-6 sm:pb-8">
        <Skeleton className="h-9 w-3/4 max-w-[520px] sm:h-12" />
        <Skeleton className="mt-4 h-5 w-full max-w-[640px]" />
      </div>
      {[0, 1].map((row) => (
        <div
          key={row}
          className="flex flex-wrap gap-x-12 gap-y-4 border-b border-rule py-8 sm:py-10"
        >
          <Skeleton className="h-8 flex-[1_1_280px]" />
          <div className="flex flex-[999_1_640px] flex-col gap-3">
            <Skeleton className="h-5 w-full" />
            <Skeleton className="h-5 w-11/12" />
            <Skeleton className="h-5 w-2/3" />
          </div>
        </div>
      ))}
    </div>
  );
}

/** Shown while the (app) layout asks the API who is signed in. */
export function ShellSkeleton() {
  return (
    <>
      <BrandBar />
      <div className="mx-auto w-full max-w-[1280px] px-4 pt-6 sm:px-8 sm:pt-12">
        <PageSkeleton />
      </div>
    </>
  );
}
