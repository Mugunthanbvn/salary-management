import { render } from "@testing-library/react";
import {
  NuqsTestingAdapter,
  type OnUrlUpdateFunction,
} from "nuqs/adapters/testing";
import type { ReactElement } from "react";

import { MeProvider } from "@/components/shell/me-context";
import type { Me } from "@/lib/permissions";

import { makeMe } from "./fixtures";

type Options = {
  /** Who is signed in (GET /auth/me); an HR manager by default. */
  me?: Me;
  /** The page's query string, e.g. "?country=DE&page=2". */
  searchParams?: string;
  /** Called with each URL update a component makes (nuqs). */
  onUrlUpdate?: OnUrlUpdateFunction;
  /** Real debounce timings for URL updates; off (0) by default. */
  rateLimitFactor?: number;
};

/** Renders a Client Component as it runs in the (app) shell: signed in, with URL state. */
export function renderInApp(
  ui: ReactElement,
  {
    me = makeMe(),
    searchParams = "",
    onUrlUpdate,
    rateLimitFactor = 0,
  }: Options = {},
) {
  return render(
    <NuqsTestingAdapter
      searchParams={searchParams}
      onUrlUpdate={onUrlUpdate}
      rateLimitFactor={rateLimitFactor}
      hasMemory
    >
      <MeProvider me={me}>{ui}</MeProvider>
    </NuqsTestingAdapter>,
  );
}
