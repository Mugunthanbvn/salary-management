import type { components } from "@/lib/api/schema";

type Role = components["schemas"]["Role"];

/**
 * How a role is named on screen ("Hema Iyer, HR Manager"). Display only: the UI never
 * decides anything from a role name; it checks permissions (lib/permissions.ts).
 */
export const ROLE_LABELS: Record<Role, string> = {
  ADMIN: "Admin",
  HR_MANAGER: "HR Manager",
  VIEWER: "Viewer",
};
