"use client";

import { useQueryStates } from "nuqs";
import {
  createContext,
  use,
  useTransition,
  type ReactNode,
  type TransitionStartFunction,
} from "react";

import { directoryParsers } from "@/lib/directory-params";

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
