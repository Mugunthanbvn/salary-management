import type { ReactNode } from "react";

import type { Explained } from "./messages";

/** A refusal in red pen: what went wrong, and what to do next. */
export function ProblemNote({
  id,
  problem,
  children,
}: {
  id?: string;
  problem: Explained;
  /** More detail under the message, e.g. the rows a commit found in the way. */
  children?: ReactNode;
}) {
  return (
    <div id={id} role="alert" className="mt-4 max-w-[720px]">
      <p className="text-[17px] leading-normal font-bold text-ink red-pen">
        {problem.message}
      </p>
      {problem.more ? (
        <p className="mt-2 text-[15px] break-words text-ink-2">
          {problem.more}
        </p>
      ) : null}
      {children}
    </div>
  );
}
