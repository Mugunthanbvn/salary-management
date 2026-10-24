import Link from "next/link";

import { PageTitle } from "@/components/print";
import { BrandBar } from "@/components/shell/brand-bar";

/** For an address that matches no page. */
export default function NotFound() {
  return (
    <>
      <BrandBar />
      <main className="mx-auto max-w-[1280px] px-4 pt-8 pb-16 sm:px-8 sm:pt-12">
        <PageTitle title="This page doesn't exist">
          Check the address, or start again from Insights.
        </PageTitle>
        <Link
          href="/insights"
          className="mt-6 inline-flex min-h-11 items-center text-base font-bold"
        >
          Go to Insights
        </Link>
      </main>
    </>
  );
}
