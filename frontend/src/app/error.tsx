"use client";

import { ErrorState } from "@/components/print";
import { BrandBar } from "@/components/shell/brand-bar";

/**
 * For errors outside a page that nothing else shows, e.g. the API not answering at all while
 * the shell loads (an API problem is shown by AppShell itself, with its request id).
 * Errors inside pages use (app)/error.tsx.
 */
export default function RootError({
  retry,
}: {
  error: unknown;
  retry: () => void;
}) {
  return (
    <>
      <BrandBar />
      <main className="mx-auto max-w-[1280px] px-4 pt-8 pb-16 sm:px-8 sm:pt-12">
        <ErrorState
          title="ACME Pay couldn't load"
          detail="We couldn't reach the server. Try again, or come back in a few minutes."
          onRetry={retry}
        />
      </main>
    </>
  );
}
