"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { useMe } from "./me-context";
import { isCurrent, mainNavItems } from "./nav-items";

/**
 * The phone navigation (< 640 px): a bar fixed to the bottom of the screen, clear of the
 * home indicator (safe-area inset). The (app) layout pads the page so nothing hides under it.
 */
export function BottomNav() {
  const me = useMe();
  const pathname = usePathname();
  return (
    <nav
      aria-label="Main"
      className="fixed inset-x-0 bottom-0 z-40 border-t border-rule bg-paper pb-[env(safe-area-inset-bottom)] sm:hidden"
    >
      <ul className="flex">
        {mainNavItems(me).map((item) => {
          const current = isCurrent(pathname, item.href);
          return (
            <li key={item.href} className="flex-1">
              <Link
                href={item.href}
                aria-current={current ? "page" : undefined}
                className={
                  current
                    ? "flex min-h-14 items-center justify-center text-sm font-bold text-ink underline decoration-2 underline-offset-[6px] hover:text-ink"
                    : "flex min-h-14 items-center justify-center text-sm text-ink-2 no-underline hover:text-ink"
                }
              >
                {item.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
