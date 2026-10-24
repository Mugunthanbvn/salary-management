import {
  EmptyState,
  ErrorState,
  Highlight,
  MarginNote,
  Section,
  StatusWord,
} from "@/components/print";
import { Count, Hidden } from "@/components/insights/figures";
import type { Result } from "@/components/insights/result";
import type { components } from "@/lib/api/schema";
import { formatPercent, formatRatio } from "@/lib/numbers";

import { RatioStrip } from "./band-strip";

type S = components["schemas"];

export const TEAMS_QUESTION = "Is any team paid below its bands?";

/** The answer in one sentence, from the API's `below_threshold` flags. */
function TeamsAnswer({ data }: { data: S["PayEquityDepartments"] }) {
  const below = data.groups.filter((group) => group.below_threshold);
  const [first, ...others] = below;
  if (!first) {
    return (
      <>
        No. Every team&apos;s median compa-ratio is at least{" "}
        {formatRatio(data.thresholds.rollup)}, so no team as a whole sits below
        its bands.
      </>
    );
  }
  return (
    <>
      Yes.{" "}
      <Highlight>
        {first.department.name} has a median compa-ratio of{" "}
        {first.median_compa_ratio !== null
          ? formatRatio(first.median_compa_ratio)
          : "—"}
      </Highlight>
      , so the team as a whole sits under the middle of its bands
      {others.length > 0
        ? `, and so ${others.length === 1 ? "does" : "do"} ${others.map((group) => group.department.name).join(", ")}`
        : ""}
      .
    </>
  );
}

/** "Is any team paid below its bands?": GET /insights/pay-equity?view=departments. */
export function TeamView({
  result,
}: {
  result: Result<S["PayEquityDepartments"]>;
}) {
  if (!result.data) {
    return (
      <Section question={TEAMS_QUESTION}>
        <ErrorState {...result.problem} />
      </Section>
    );
  }
  const { groups, thresholds } = result.data;
  if (groups.length === 0) {
    return (
      <Section question={TEAMS_QUESTION}>
        <EmptyState title="No teams to compare">
          Nobody here has a pay band to compare with.
        </EmptyState>
      </Section>
    );
  }

  return (
    <Section question={TEAMS_QUESTION}>
      <p className="mb-6 font-serif text-xl leading-snug sm:text-2xl">
        <TeamsAnswer data={result.data} />
      </p>
      <table className="w-full border-collapse text-[15px] tabular-nums">
        <thead>
          <tr className="text-left text-[13px] text-ink-2">
            <th scope="col" className="pr-3 pb-2 font-medium">
              Team
            </th>
            <th
              scope="col"
              className="hidden w-[38%] px-3 pb-2 font-medium sm:table-cell"
            >
              <span className="flex justify-between">
                <span>{formatRatio(thresholds.low)}</span>
                <span className="font-bold text-ink">1.00</span>
                <span>{formatRatio(thresholds.high)}</span>
              </span>
            </th>
            <th scope="col" className="px-3 pb-2 text-right font-medium">
              Median compa-ratio
            </th>
            <th scope="col" className="pb-2 pl-3 text-right font-medium">
              Below band
            </th>
          </tr>
        </thead>
        <tbody>
          {groups.map((group) => {
            const flagged = group.below_threshold === true;
            return (
              <tr key={group.department.id} className="border-t border-rule">
                <th
                  scope="row"
                  className={`py-3 pr-3 text-left ${flagged ? "font-bold text-red-pen" : "font-normal"}`}
                >
                  {group.department.name}
                  {flagged ? (
                    <span className="mt-0.5 block text-sm">
                      <StatusWord tone="problem">
                        Below band as a team
                      </StatusWord>
                    </span>
                  ) : null}
                  <span className="mt-0.5 block text-[13px] font-normal text-ink-3">
                    <Count value={group.count} /> people
                  </span>
                </th>
                <td className="hidden px-3 py-3 sm:table-cell">
                  <RatioStrip
                    ratio={group.median_compa_ratio}
                    thresholds={thresholds}
                    flagged={flagged}
                  />
                </td>
                <td
                  className={`px-3 py-3 text-right font-bold ${flagged ? "text-red-pen" : ""}`}
                >
                  {group.median_compa_ratio !== null ? (
                    formatRatio(group.median_compa_ratio)
                  ) : (
                    <Hidden />
                  )}
                </td>
                <td className="py-3 pl-3 text-right text-ink-2">
                  {group.pct_below_band !== null ? (
                    formatPercent(group.pct_below_band)
                  ) : (
                    <Hidden />
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <MarginNote className="mt-3">
        Dashed line at {formatRatio(thresholds.rollup)}: a team whose median
        falls below it is flagged as paid below band as a team. &ldquo;Below
        band&rdquo; is the share of the team paid under its band minimum.
      </MarginNote>
    </Section>
  );
}
