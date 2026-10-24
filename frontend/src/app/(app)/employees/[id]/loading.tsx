import { Skeleton } from "@/components/ui/skeleton";

/** An employee's page while it loads: back link, name and summary, then three sections. */
export default function EmployeeLoading() {
  return (
    <div aria-busy="true">
      <p className="sr-only" role="status">
        Loading the employee…
      </p>
      <Skeleton className="mb-4 h-5 w-36 sm:-mt-4" />
      <div className="border-b-2 border-ink pb-6 sm:pb-8">
        <Skeleton className="h-9 w-2/3 max-w-[420px] sm:h-12" />
        <Skeleton className="mt-4 h-5 w-full max-w-[640px]" />
      </div>
      {[0, 1, 2].map((section) => (
        <div
          key={section}
          className="flex flex-wrap gap-x-12 gap-y-4 border-b border-rule py-8 sm:py-10"
        >
          <Skeleton className="h-8 flex-[1_1_280px]" />
          <div className="flex flex-[999_1_640px] flex-col gap-3">
            <Skeleton className="h-10 w-1/2" />
            <Skeleton className="h-5 w-full max-w-[560px]" />
            <Skeleton className="h-5 w-full max-w-[560px]" />
            <Skeleton className="h-5 w-2/3 max-w-[560px]" />
          </div>
        </div>
      ))}
    </div>
  );
}
