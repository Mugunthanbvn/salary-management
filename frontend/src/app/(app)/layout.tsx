import { Suspense, type ReactNode } from "react";

import { AppHeader } from "@/components/shell/app-header";
import { BottomNav } from "@/components/shell/bottom-nav";
import { MeProvider } from "@/components/shell/me-context";
import { ShellSkeleton } from "@/components/shell/skeletons";
import { getMe } from "@/lib/api/me";

/**
 * The signed-in shell around every page except /login. It asks the API who is signed in
 * (GET /auth/me; a 401 goes to /login) and hands that to Client Components via useMe().
 * The session read happens behind <Suspense>, as Cache Components requires.
 */
export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <Suspense fallback={<ShellSkeleton />}>
      <Shell>{children}</Shell>
    </Suspense>
  );
}

async function Shell({ children }: { children: ReactNode }) {
  const me = await getMe();
  return (
    <MeProvider me={me}>
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:bg-paper focus:p-3"
      >
        Skip to content
      </a>
      <AppHeader />
      {/* On phones, the bottom padding keeps the end of the page above the fixed bottom bar. */}
      <main
        id="main"
        className="mx-auto w-full max-w-[1280px] px-4 pt-6 pb-[calc(3.5rem+env(safe-area-inset-bottom)+2rem)] sm:px-8 sm:pt-12 sm:pb-20"
      >
        {children}
      </main>
      <BottomNav />
    </MeProvider>
  );
}
