"use client";

import type { ReactNode } from "react";

import type { components } from "@/lib/api/schema";

type ReferenceData = components["schemas"]["ReferenceData"];

export function NewEmployeeForm({
  reference,
}: {
  reference: ReferenceData;
}): ReactNode {
  void reference;
  throw new Error("NewEmployeeForm is not implemented yet");
}
