import Link from "next/link";

import { PageTitle } from "@/components/print";

/** Inside the shell, for a page that calls notFound() (e.g. an unknown employee). */
export default function AppNotFound() {
  return (
    <>
      <PageTitle title="This page doesn't exist">
        It may have moved, or the link may be wrong.
      </PageTitle>
      <Link
        href="/insights"
        className="mt-6 inline-flex min-h-11 items-center text-base font-bold"
      >
        Go to Insights
      </Link>
    </>
  );
}
