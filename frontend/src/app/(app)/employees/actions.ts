"use server";

/**
 * The employee mutations (docs/13-frontend-ux.md §3.1): each calls FastAPI as the signed-in
 * person, then refreshes the pages that show the change. FastAPI checks the permission,
 * the version and every rule; a problem comes back as plain data for the form to show.
 * Server Actions are public endpoints: the arguments are untrusted, and the API validates
 * them (unknown fields are refused).
 */
import { revalidatePath } from "next/cache";

import { toPlainProblem, type ActionResult } from "@/lib/api/action-result";
import { toProblem } from "@/lib/api/problem";
import type { components } from "@/lib/api/schema";
import { serverApi } from "@/lib/api/server";

type SalaryChange = components["schemas"]["SalaryChange"];
type SalaryChangeRequest = components["schemas"]["SalaryChangeRequest"];
type EmployeeDetail = components["schemas"]["EmployeeDetail"];
type EmployeeCreate = components["schemas"]["EmployeeCreate"];
type EmployeeUpdate = components["schemas"]["EmployeeUpdate"];
type TerminateRequest = components["schemas"]["TerminateRequest"];
type ReactivateRequest = components["schemas"]["ReactivateRequest"];

type ApiResult<T> = { data?: T; error?: unknown; response: Response };
type Api = Awaited<ReturnType<typeof serverApi>>;

export async function recordSalaryChange(
  employeeId: number,
  body: SalaryChangeRequest,
): Promise<ActionResult<SalaryChange>> {
  return changeEmployee(employeeId, (api, path) =>
    api.POST("/api/v1/employees/{employee_id}/salary-changes", {
      params: { path },
      body,
    }),
  );
}

export async function updateEmployee(
  employeeId: number,
  body: EmployeeUpdate,
): Promise<ActionResult<EmployeeDetail>> {
  return changeEmployee(employeeId, (api, path) =>
    api.PATCH("/api/v1/employees/{employee_id}", { params: { path }, body }),
  );
}

export async function terminateEmployee(
  employeeId: number,
  body: TerminateRequest,
): Promise<ActionResult<EmployeeDetail>> {
  return changeEmployee(employeeId, (api, path) =>
    api.POST("/api/v1/employees/{employee_id}/terminate", {
      params: { path },
      body,
    }),
  );
}

export async function reactivateEmployee(
  employeeId: number,
  body: ReactivateRequest,
): Promise<ActionResult<EmployeeDetail>> {
  return changeEmployee(employeeId, (api, path) =>
    api.POST("/api/v1/employees/{employee_id}/reactivate", {
      params: { path },
      body,
    }),
  );
}

export async function createEmployee(
  body: EmployeeCreate,
): Promise<ActionResult<EmployeeDetail>> {
  const result = await call(async () =>
    (await serverApi()).POST("/api/v1/employees", { body }),
  );
  if (result.ok) revalidatePath("/employees");
  return result;
}

/** A change to one employee: their page and the directory show it afterwards. */
async function changeEmployee<T>(
  employeeId: number,
  request: (api: Api, path: { employee_id: number }) => Promise<ApiResult<T>>,
): Promise<ActionResult<T>> {
  if (!Number.isSafeInteger(employeeId) || employeeId < 1) {
    return { ok: false, problem: NOT_FOUND };
  }
  const result = await call(async () =>
    request(await serverApi(), { employee_id: employeeId }),
  );
  if (result.ok) {
    revalidatePath(`/employees/${employeeId}`);
    revalidatePath("/employees");
  }
  return result;
}

async function call<T>(
  request: () => Promise<ApiResult<T>>,
): Promise<ActionResult<T>> {
  let result: ApiResult<T>;
  try {
    result = await request();
  } catch {
    // The network failed before FastAPI could answer.
    return { ok: false, problem: UNREACHABLE };
  }
  if (result.data !== undefined) return { ok: true, data: result.data };
  const problem = await toProblem(result.response, result.error);
  return { ok: false, problem: toPlainProblem(problem) };
}

const UNREACHABLE = {
  slug: null,
  title: "Couldn't reach ACME Pay",
  status: 503,
  detail: "Nothing was changed. Check your connection and try again.",
  errors: [],
  requestId: null,
  currentVersion: null,
};

const NOT_FOUND = {
  slug: "not-found",
  title: "Not found",
  status: 404,
  detail: "There is no such employee.",
  errors: [],
  requestId: null,
  currentVersion: null,
};
