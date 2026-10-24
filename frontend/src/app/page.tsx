import { Suspense } from "react";

import { ApiStatus } from "@/components/api-status";
import { getApiHealth } from "@/lib/api/health";
import { API_ORIGIN } from "@/lib/api/origin";

export default function HomePage() {
  return (
    <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-4 px-4 py-12 sm:px-8">
      <h1 className="text-4xl font-semibold">ACME Pay</h1>
      <Suspense fallback={<p>Checking the API…</p>}>
        <HealthCheck />
      </Suspense>
    </main>
  );
}

// Runs on every request. With Cache Components the uncached fetch streams in behind the
// Suspense fallback, so the heading is prerendered and `next build` needs no backend.
async function HealthCheck() {
  const status = await getApiHealth(API_ORIGIN);
  return <ApiStatus status={status} />;
}
