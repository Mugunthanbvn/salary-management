"use client";

import { useQueryStates } from "nuqs";
import {
  createContext,
  use,
  useTransition,
  type ReactNode,
  type TransitionStartFunction,
} from "react";

import { insightsParsers, payEquityParsers } from "@/lib/insights-params";

type Transition = {
  isPending: boolean;
  startTransition: TransitionStartFunction;
};

const InsightsTransition = createContext<Transition | null>(null);

/**
 * One transition for every control of a dashboard: while the server renders the new
 * figures, the old ones stay on screen, marked busy (docs/13-frontend-ux.md §9).
 */
export function InsightsProvider({ children }: { children: ReactNode }) {
  const [isPending, startTransition] = useTransition();
  return (
    <InsightsTransition value={{ isPending, startTransition }}>
      {children}
    </InsightsTransition>
  );
}

/**
 * The dashboard's URL state (lib/insights-params.ts). A change asks the server for new
 * figures (`shallow: false`) and adds a history entry, so Back undoes it. The period is
 * display only: set it with `{ shallow: true }`.
 */
export function useInsightsState() {
  const transition = use(InsightsTransition);
  return useQueryStates(insightsParsers, {
    shallow: false,
    history: "push",
    scroll: false,
    startTransition: transition?.startTransition,
  });
}

/** The pay-equity screen's URL state: its country and department. */
export function usePayEquityState() {
  const transition = use(InsightsTransition);
  return useQueryStates(payEquityParsers, {
    shallow: false,
    history: "push",
    scroll: false,
    startTransition: transition?.startTransition,
  });
}

/** True while new figures are on their way. */
export function useInsightsPending(): boolean {
  return use(InsightsTransition)?.isPending ?? false;
}
