/**
 * Dates from the API are `YYYY-MM-DD` with no time zone. They are read and shown in UTC,
 * so a date never moves a day with the viewer's time zone, and server and browser agree.
 */

const DATE = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  year: "numeric",
  timeZone: "UTC",
});

/** `"2021-03-15"` → `"15 Mar 2021"`, the printout's date style. */
export function formatDate(iso: string): string {
  return DATE.format(new Date(`${iso}T00:00:00Z`));
}

const TIME = new Intl.DateTimeFormat("en-GB", {
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
  timeZone: "UTC",
});

/** `"2026-10-25T10:45:00Z"` → `"25 Oct 2026, 10:45 UTC"`: a timestamp, said in UTC. */
export function formatDateTime(iso: string): string {
  const instant = new Date(iso);
  return `${DATE.format(instant)}, ${TIME.format(instant)} UTC`;
}

/** Today as `YYYY-MM-DD` in UTC, which is what the API checks "no future dates" against. */
export function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}
