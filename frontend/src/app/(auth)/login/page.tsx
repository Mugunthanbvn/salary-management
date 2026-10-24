import type { Metadata } from "next";

import { PageTitle } from "@/components/print";

import { DemoAccounts } from "./demo-accounts";
import { LoginForm } from "./login-form";

export const metadata: Metadata = { title: "Sign in · ACME Pay" };

export default function LoginPage() {
  // Inlined at build time; set only on the demo deployment (docs/13-frontend-ux.md §4.1).
  const showDemoAccounts =
    process.env.NEXT_PUBLIC_SHOW_DEMO_ACCOUNTS === "true";
  return (
    <div className="min-h-dvh">
      <header className="border-b border-rule pt-[env(safe-area-inset-top)]">
        <div className="mx-auto max-w-[1280px] px-4 py-1 sm:px-8 sm:py-2">
          <span className="inline-flex min-h-11 items-center font-serif text-[20px] font-bold sm:text-[22px]">
            ACME Pay
          </span>
        </div>
      </header>
      <main className="mx-auto max-w-[1280px] px-4 pt-8 pb-16 sm:px-8 sm:pt-12">
        <div className="flex flex-wrap gap-x-12 gap-y-10">
          <div className="min-w-0 flex-[1_1_320px] sm:max-w-[520px]">
            <PageTitle title="Sign in to ACME Pay">
              Salary records and pay insights for ACME&apos;s HR team.
            </PageTitle>
            <div className="mt-8">
              <LoginForm />
            </div>
          </div>
          {showDemoAccounts ? <DemoAccounts /> : null}
        </div>
      </main>
    </div>
  );
}
