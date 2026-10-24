import type { Metadata } from "next";

import { PageTitle } from "@/components/print";
import { BrandBar } from "@/components/shell/brand-bar";

import { DemoAccounts } from "./demo-accounts";
import { LoginForm } from "./login-form";

export const metadata: Metadata = { title: "Sign in" };

export default function LoginPage() {
  // Inlined at build time; set only on the demo deployment (docs/13-frontend-ux.md §4.1).
  const showDemoAccounts =
    process.env.NEXT_PUBLIC_SHOW_DEMO_ACCOUNTS === "true";
  return (
    <>
      <BrandBar />
      <main className="mx-auto max-w-[1280px] pt-8 page-gutter pb-16 sm:pt-12">
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
    </>
  );
}
