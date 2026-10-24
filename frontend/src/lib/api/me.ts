import "server-only";

import type { Me } from "@/lib/permissions";

export function getMe(): Promise<Me> {
  throw new Error("getMe is not implemented yet");
}
