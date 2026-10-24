/**
 * UI-only permission helpers: they decide what to hide, never what is allowed. FastAPI
 * checks every request (docs/13-frontend-ux.md §3.5). Check permissions, never role names.
 */
import type { components } from "@/lib/api/schema";

/** The signed-in person, as GET /api/v1/auth/me returns them. */
export type Me = components["schemas"]["MeResponse"];
export type Permission = components["schemas"]["Permission"];

/** True when the person's role grants this permission. */
export function can(me: Me, permission: Permission): boolean {
  return me.permissions.includes(permission);
}

export function canAsk(me: Me): boolean {
  void me;
  throw new Error("canAsk is not implemented yet");
}
