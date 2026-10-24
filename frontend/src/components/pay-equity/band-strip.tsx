import type { components } from "@/lib/api/schema";
import { positionPercent, stripScale } from "@/lib/position";

type S = components["schemas"];

/**
 * A cohort's pay drawn as a position in its band (DESIGN.md "pay shown as a position in a
 * band"): the band min–max as an outlined box, its midpoint as a tick, the middle half
 * (P25–P75) as a thick ink bar and the median as a dot. Every mark is placed from the
 * API's figures; the figures themselves are written out next to it, so it is aria-hidden.
 */
export function BandStrip({
  band,
  stats,
}: {
  band: S["Band"];
  stats: Pick<S["Stats"], "p25" | "median" | "p75">;
}) {
  const scale = stripScale(band, [stats.p25, stats.median, stats.p75]);
  const at = (value: number) => positionPercent(value, scale.lo, scale.hi);
  const bandFrom = at(band.min);
  const bandTo = at(band.max);

  return (
    <span
      aria-hidden="true"
      data-testid="band-strip"
      className="relative block h-5 w-full"
    >
      <span className="absolute inset-x-0 top-[9px] h-0.5 bg-rule" />
      <span
        data-mark="band"
        className="absolute top-1 h-3 border border-ink-3"
        style={{ left: `${bandFrom}%`, width: `${bandTo - bandFrom}%` }}
      />
      <span
        data-mark="mid"
        className="absolute top-0 h-5 w-px bg-ink-3"
        style={{ left: `${at(band.mid)}%` }}
      />
      {stats.p25 !== null && stats.p75 !== null ? (
        <span
          data-mark="middle-half"
          className="absolute top-2 h-1 bg-ink"
          style={{
            left: `${at(stats.p25)}%`,
            width: `${at(stats.p75) - at(stats.p25)}%`,
          }}
        />
      ) : null}
      {stats.median !== null ? (
        <span
          data-mark="median"
          className="absolute top-[3px] -ml-[7px] size-3.5 rounded-full border-2 border-paper bg-ink"
          style={{ left: `${at(stats.median)}%` }}
        />
      ) : null}
    </span>
  );
}

/**
 * A team's median compa-ratio as a dot on the low…high scale of the API's thresholds,
 * with the band middle (1.00) and the team threshold (dashed) marked.
 */
export function RatioStrip({
  ratio,
  thresholds,
  flagged,
}: {
  ratio: string | null;
  thresholds: S["Thresholds"];
  flagged: boolean;
}) {
  const at = (value: string) =>
    positionPercent(value, thresholds.low, thresholds.high);
  return (
    <span aria-hidden="true" className="relative block h-5 w-full">
      <span className="absolute inset-x-0 top-[9px] h-0.5 bg-rule" />
      <span
        className="absolute top-0 h-5 w-px bg-ink"
        style={{ left: `${at("1.00")}%` }}
      />
      <span
        className="absolute top-0 h-5 border-l border-dashed border-ink-3"
        style={{ left: `${at(thresholds.rollup)}%` }}
      />
      {ratio !== null ? (
        <span
          data-mark="ratio"
          className={`absolute top-[3px] -ml-[7px] size-3.5 rounded-full ${flagged ? "bg-red-pen" : "bg-ink"}`}
          style={{ left: `${at(ratio)}%` }}
        />
      ) : null}
    </span>
  );
}
