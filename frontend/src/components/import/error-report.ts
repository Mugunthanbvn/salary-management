import type { components } from "@/lib/api/schema";

type ImportRowError = components["schemas"]["ImportRowError"];

export function problemsCsv(errors: ImportRowError[]): string {
  void errors;
  throw new Error("problemsCsv is not implemented yet");
}

export function errorReportName(filename: string): string {
  void filename;
  throw new Error("errorReportName is not implemented yet");
}
