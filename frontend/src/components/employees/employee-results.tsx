"use client";

import type { ReactNode } from "react";

import type { components } from "@/lib/api/schema";

type EmployeePage = components["schemas"]["EmployeePage"];
type ReferenceData = components["schemas"]["ReferenceData"];

export function EmployeeResults({
  page,
  reference,
}: {
  page: EmployeePage;
  reference: ReferenceData;
}): ReactNode {
  void [page, reference];
  throw new Error("EmployeeResults is not implemented yet");
}
