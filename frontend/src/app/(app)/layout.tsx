import { Suspense, type ReactNode } from "react";

import { AppShell } from "@/components/shell/app-shell";
import { ShellSkeleton } from "@/components/shell/skeletons";

/**
 * Every page except /login sits in the signed-in shell. Reading the session happens behind
 * <Suspense>, as Cache Components requires; the skeleton shows meanwhile.
 */
export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <Suspense fallback={<ShellSkeleton />}>
      <AppShell>{children}</AppShell>
    </Suspense>
  );
}
