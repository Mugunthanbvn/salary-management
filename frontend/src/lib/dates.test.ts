import { afterEach, describe, expect, it, vi } from "vitest";

import { formatDate, todayIso } from "./dates";

describe("formatDate", () => {
  it.each([
    { iso: "2021-03-15", text: "15 Mar 2021" },
    { iso: "2026-10-01", text: "1 Oct 2026" },
    { iso: "2024-12-31", text: "31 Dec 2024" },
  ])("shows $iso as $text, the same in every time zone", ({ iso, text }) => {
    expect(formatDate(iso)).toBe(text);
  });
});

describe("todayIso", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("is today's date in UTC, the API's 'today'", () => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date("2026-10-24T23:30:00-05:00"));

    expect(todayIso()).toBe("2026-10-25");
  });
});
