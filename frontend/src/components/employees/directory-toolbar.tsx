"use client";

import type { ReactNode } from "react";

import type { components } from "@/lib/api/schema";

type ReferenceData = components["schemas"]["ReferenceData"];

export function DirectoryToolbar({
  reference,
  total,
}: {
  reference: ReferenceData;
  total: number;
}): ReactNode {
  void [reference, total];
  throw new Error("DirectoryToolbar is not implemented yet");
}
