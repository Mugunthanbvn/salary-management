import type { components, paths } from "@/lib/api/schema";

type ReferenceData = components["schemas"]["ReferenceData"];
export type ListQuery = NonNullable<
  paths["/api/v1/employees"]["get"]["parameters"]["query"]
>;
export type DirectoryState = Record<string, unknown>;

export function loadDirectoryParams(input: string): DirectoryState {
  void input;
  throw new Error("loadDirectoryParams is not implemented yet");
}

export function serializeDirectory(state: DirectoryState): string {
  void state;
  throw new Error("serializeDirectory is not implemented yet");
}

export function salaryCurrency(
  state: DirectoryState,
  reference: ReferenceData,
): string | null {
  void [state, reference];
  throw new Error("salaryCurrency is not implemented yet");
}

export function toListQuery(
  state: DirectoryState,
  options: { canReadSalaries: boolean; reference: ReferenceData },
): ListQuery {
  void [state, options];
  throw new Error("toListQuery is not implemented yet");
}
