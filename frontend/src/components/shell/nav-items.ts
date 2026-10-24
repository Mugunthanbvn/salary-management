import type { Me } from "@/lib/permissions";

export type NavItem = { href: string; label: string };

/**
 * The main navigation (docs/13-frontend-ux.md §2): the same items in the desktop top bar
 * and the phone bottom bar. Ask appears only when the API has it on and the person may ask.
 */
export function mainNavItems(me: Me): NavItem[] {
  void me;
  return [
    { href: "/insights", label: "Insights" },
    { href: "/employees", label: "Employees" },
    { href: "/ask", label: "Ask" },
  ];
}

/** /insights is current on /insights and /insights/pay-equity, not on /insightsx. */
export function isCurrent(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}
