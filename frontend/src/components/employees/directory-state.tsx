"use client";

import { useQueryStates } from "nuqs";
import {
  createContext,
  use,
  useTransition,
  type ReactNode,
  type TransitionStartFunction,
} from "react";

import { directoryParsers, type DirectoryState } from "@/lib/directory-params";

type Transition = {
  isPending: boolean;
  startTransition: TransitionStartFunction;
};

const DirectoryTransition = createContext<Transition | null>(null);

/**
 * One transition for every control of the directory: while the server renders the new
 * list, the old one stays on screen, marked busy (docs/13-frontend-ux.md §9).
 */
export function DirectoryProvider({ children }: { children: ReactNode }) {
  const [isPending, startTransition] = useTransition();
  return (
    <DirectoryTransition value={{ isPending, startTransition }}>
      {children}
    </DirectoryTransition>
  );
}

/**
 * The directory's URL state (lib/directory-params.ts). A change asks the server for the
 * new list (`shallow: false`) and adds a history entry, so Back undoes it.
 */
export function useDirectoryState() {
  const transition = use(DirectoryTransition);
  return useQueryStates(directoryParsers, {
    shallow: false,
    history: "push",
    scroll: false,
    startTransition: transition?.startTransition,
  });
}

/** True while a new list is on its way. */
export function useDirectoryPending(): boolean {
  return use(DirectoryTransition)?.isPending ?? false;
}

/** The URL keys "Clear filters" resets; sort, page size and the pay toggles stay. */
export const CLEARED_FILTERS = {
  q: null,
  country: null,
  department_id: null,
  job_role_id: null,
  level: null,
  employment_type: null,
  status: null,
  currency: null,
  salary_min: null,
  salary_max: null,
  salary_basis: null,
  page: null,
} as const;

/** True when anything narrows the list beyond the default (active employees). */
export function hasFilters(state: DirectoryState): boolean {
  return (
    state.q.trim() !== "" ||
    state.country.length > 0 ||
    state.department_id.length > 0 ||
    state.job_role_id.length > 0 ||
    state.level.length > 0 ||
    state.employment_type.length > 0 ||
    state.currency.length > 0 ||
    !isDefaultStatus(state.status) ||
    state.salary_min !== null ||
    state.salary_max !== null
  );
}

export function isDefaultStatus(status: DirectoryState["status"]): boolean {
  return status.length === 1 && status[0] === "ACTIVE";
}
