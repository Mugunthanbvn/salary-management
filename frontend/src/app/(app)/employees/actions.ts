"use server";

import type { ActionResult } from "@/lib/api/action-result";
import type { components } from "@/lib/api/schema";

type SalaryChange = components["schemas"]["SalaryChange"];
type SalaryChangeRequest = components["schemas"]["SalaryChangeRequest"];
type EmployeeDetail = components["schemas"]["EmployeeDetail"];
type EmployeeCreate = components["schemas"]["EmployeeCreate"];
type EmployeeUpdate = components["schemas"]["EmployeeUpdate"];
type TerminateRequest = components["schemas"]["TerminateRequest"];
type ReactivateRequest = components["schemas"]["ReactivateRequest"];

export async function recordSalaryChange(
  employeeId: number,
  body: SalaryChangeRequest,
): Promise<ActionResult<SalaryChange>> {
  void [employeeId, body];
  return Promise.reject(new Error("recordSalaryChange is not implemented yet"));
}

export async function updateEmployee(
  employeeId: number,
  body: EmployeeUpdate,
): Promise<ActionResult<EmployeeDetail>> {
  void [employeeId, body];
  return Promise.reject(new Error("updateEmployee is not implemented yet"));
}

export async function terminateEmployee(
  employeeId: number,
  body: TerminateRequest,
): Promise<ActionResult<EmployeeDetail>> {
  void [employeeId, body];
  return Promise.reject(new Error("terminateEmployee is not implemented yet"));
}

export async function reactivateEmployee(
  employeeId: number,
  body: ReactivateRequest,
): Promise<ActionResult<EmployeeDetail>> {
  void [employeeId, body];
  return Promise.reject(new Error("reactivateEmployee is not implemented yet"));
}

export async function createEmployee(
  body: EmployeeCreate,
): Promise<ActionResult<EmployeeDetail>> {
  void body;
  return Promise.reject(new Error("createEmployee is not implemented yet"));
}
