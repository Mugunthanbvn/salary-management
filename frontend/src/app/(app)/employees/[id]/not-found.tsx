import Link from "next/link";

import { PageTitle } from "@/components/print";

/** For an id that is no employee (the page calls notFound()). */
export default function EmployeeNotFound() {
  return (
    <>
      <PageTitle title="We can't find this employee">
        The link may be wrong, or the id may be mistyped.
      </PageTitle>
      <Link
        href="/employees"
        className="mt-6 inline-flex min-h-11 items-center text-base font-bold"
      >
        Back to employees
      </Link>
    </>
  );
}
