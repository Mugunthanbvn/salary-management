import type { ReactNode } from "react";

import { getMe } from "@/lib/api/me";

import { AppHeader } from "./app-header";
import { BottomNav } from "./bottom-nav";
import { MeProvider } from "./me-context";

/**
 * The signed-in frame (a Server Component): asks the API who is signed in (GET /auth/me;
 * a 401 goes to /login), hands that to Client Components via useMe(), and renders the top
 * bar, the page and the phone bottom bar. It reads cookies(), so render it in <Suspense>.
 */
export async function AppShell({ children }: { children: ReactNode }) {
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
