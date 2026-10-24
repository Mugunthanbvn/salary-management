import type { components } from "@/lib/api/schema";

type MeResponse = components["schemas"]["MeResponse"];
type Permission = components["schemas"]["Permission"];

// Test data mirroring ROLE_PERMISSIONS in backend/src/salary_api/core/permissions.py.
// The UI never derives permissions from a role; it reads them from GET /auth/me.
export const HR_MANAGER_PERMISSIONS: Permission[] = [
  "EMPLOYEE_READ",
  "EMPLOYEE_WRITE",
  "SALARY_READ",
  "SALARY_WRITE",
  "INSIGHTS_READ",
  "EXPORT",
  "IMPORT",
  "ASK",
];

export const VIEWER_PERMISSIONS: Permission[] = [
  "EMPLOYEE_READ",
  "INSIGHTS_READ",
  "EXPORT",
  "ASK",
];

/** A GET /auth/me body for an HR manager with Ask on; override what the test is about. */
export function makeMe(overrides: Partial<MeResponse> = {}): MeResponse {
  return {
    user: {
      id: 2,
      email: "hr@acme.example",
      full_name: "Hema Iyer",
      role: "HR_MANAGER",
    },
    permissions: HR_MANAGER_PERMISSIONS,
    features: { ask: true },
    ...overrides,
  };
}
