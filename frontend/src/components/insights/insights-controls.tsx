"use client";

import type { components } from "@/lib/api/schema";

type ReferenceData = components["schemas"]["ReferenceData"];

export function InsightsControls({ reference }: { reference: ReferenceData }) {
  void reference;
  throw new Error("InsightsControls is not implemented yet");
}
