import "server-only";

import type { Client } from "openapi-fetch";

import type { paths } from "./schema";

export function serverApi(): Promise<Client<paths>> {
  throw new Error("serverApi is not implemented yet");
}
