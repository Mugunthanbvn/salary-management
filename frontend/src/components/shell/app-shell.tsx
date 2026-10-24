import type { ReactNode } from "react";

import { ErrorState } from "@/components/print";
import { getMe } from "@/lib/api/me";
import { ProblemError } from "@/lib/api/problem";
import type { Me } from "@/lib/permissions";

import { AppHeader } from "./app-header";
import { BottomNav } from "./bottom-nav";
import { BrandBar } from "./brand-bar";
import { MeProvider } from "./me-context";

/**
 * The signed-in frame (a Server Component): asks the API who is signed in (GET /auth/me;
 * a 401 goes to /login), hands that to Client Components via useMe(), and renders the top
 * bar, the page and the phone bottom bar. It reads cookies(), so render it in <Suspense>.
 */
export async function AppShell({ children }: { children: ReactNode }) {
  let me: Me;
  try {
    me = await getMe();
  } catch (error) {
    // Rendered here, on the server: thrown, the problem would reach the browser as a
    // generic message (production hides server error messages). Anything else, including
    // the redirect to /login, carries on to Next and the root error page.
    if (error instanceof ProblemError) return <ShellProblem problem={error} />;
    throw error;
  }
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
        className="mx-auto w-full max-w-[1280px] pt-6 page-gutter pb-[calc(3.5rem+env(safe-area-inset-bottom)+2rem)] sm:pt-12 sm:pb-20"
      >
        {children}
      </main>
      <BottomNav />
    </MeProvider>
  );
}

function ShellProblem({ problem }: { problem: ProblemError }) {
  return (
    <>
      <BrandBar />
      <main className="mx-auto max-w-[1280px] pt-8 page-gutter pb-16 sm:pt-12">
        <ErrorState
          title={problem.title}
          detail={problem.detail}
          requestId={problem.requestId}
        />
      </main>
    </>
  );
}
