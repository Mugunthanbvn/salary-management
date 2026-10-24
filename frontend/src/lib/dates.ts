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

/** Today as `YYYY-MM-DD` in UTC, which is what the API checks "no future dates" against. */
export function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}
