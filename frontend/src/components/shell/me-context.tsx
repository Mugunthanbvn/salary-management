"use client";

import { createContext, use, useMemo, type ReactNode } from "react";

import { can, type Me, type Permission } from "@/lib/permissions";

export type MeWithCan = Me & {
  /** True when the person holds this permission. UI hiding only; the API decides. */
  can: (permission: Permission) => boolean;
};

const MeContext = createContext<MeWithCan | null>(null);

/**
 * Hands the GET /auth/me result, fetched once by the (app) layout on the server, to the
 * Client Components under it.
 */
export function MeProvider({ me, children }: { me: Me; children: ReactNode }) {
  const value = useMemo<MeWithCan>(
    () => ({ ...me, can: (permission) => can(me, permission) }),
    [me],
  );
  return <MeContext value={value}>{children}</MeContext>;
}

/** The signed-in person in a Client Component under the (app) layout. */
export function useMe(): MeWithCan {
  const me = use(MeContext);
  if (!me) throw new Error("useMe() needs a <MeProvider> above it");
  return me;
}
