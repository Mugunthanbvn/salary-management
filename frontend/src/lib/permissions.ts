import type { components } from "@/lib/api/schema";

export type Me = components["schemas"]["MeResponse"];
export type Permission = components["schemas"]["Permission"];

export function can(me: Me, permission: Permission): boolean {
  void me;
  void permission;
  throw new Error("can is not implemented yet");
}
