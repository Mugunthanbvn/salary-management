"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { AccountMenu } from "./account-menu";
import { useMe } from "./me-context";
import { isCurrent, mainNavItems } from "./nav-items";

/**
 * The top bar: "ACME Pay" and the account menu everywhere; the main links from 640 px up.
 * On phones the links move to the bottom bar (BottomNav).
 */
export function AppHeader() {
  const me = useMe();
  const pathname = usePathname();
  return (
    <header className="border-b border-rule bg-paper pt-[env(safe-area-inset-top)]">
      <div className="mx-auto flex max-w-[1280px] items-center gap-x-8 px-4 py-1 sm:px-8 sm:py-2">
        <Link
          href="/insights"
          className="inline-flex min-h-11 items-center font-serif text-[20px] font-bold text-ink no-underline hover:text-ink sm:text-[22px]"
        >
          ACME Pay
        </Link>
        <nav aria-label="Main" className="hidden flex-1 sm:block">
          <ul className="flex gap-6">
            {mainNavItems(me).map((item) => {
              const current = isCurrent(pathname, item.href);
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    aria-current={current ? "page" : undefined}
                    className={
                      current
                        ? "inline-flex min-h-11 items-center text-[15px] font-bold text-ink underline decoration-2 underline-offset-[6px] hover:text-ink"
                        : "inline-flex min-h-11 items-center text-[15px] text-ink-2 no-underline hover:text-ink hover:underline hover:underline-offset-[6px]"
                    }
                  >
                    {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
        <div className="ml-auto">
          <AccountMenu />
        </div>
      </div>
    </header>
  );
}
