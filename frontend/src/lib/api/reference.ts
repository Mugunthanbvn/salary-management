import "server-only";

import type { components } from "./schema";

type ReferenceData = components["schemas"]["ReferenceData"];

export function getReference(): Promise<ReferenceData> {
  throw new Error("getReference is not implemented yet");
}
