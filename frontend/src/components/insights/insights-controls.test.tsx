import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { UrlUpdateEvent } from "nuqs/adapters/testing";
import { describe, expect, it, vi } from "vitest";

import { makeReference } from "@/test/fixtures";
import { renderInApp } from "@/test/render";

import { InsightsControls, PayToggles } from "./insights-controls";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn(), push: vi.fn() }),
}));

function lastUpdate(onUrlUpdate: ReturnType<typeof vi.fn>): UrlUpdateEvent {
  const calls = onUrlUpdate.mock.calls as [UrlUpdateEvent][];
  const last = calls.at(-1);
  if (!last) throw new Error("the URL was not updated");
  return last[0];
}

function renderControls(searchParams = "") {
  const onUrlUpdate = vi.fn();
  renderInApp(
    <>
      <PayToggles />
      <InsightsControls reference={makeReference()} />
    </>,
    {
      searchParams,
      onUrlUpdate,
    },
  );
  return onUrlUpdate;
}

describe("InsightsControls", () => {
  it("switches to monthly in the URL without asking the server again", async () => {
    const user = userEvent.setup();
    const onUrlUpdate = renderControls();

    await user.click(screen.getByRole("button", { name: "Monthly" }));

    await waitFor(() => expect(onUrlUpdate).toHaveBeenCalled());
    expect(lastUpdate(onUrlUpdate).queryString).toBe("?period=monthly");
    expect(lastUpdate(onUrlUpdate).options.shallow).toBe(true);
  });

  it("switches to total pay, which the server fetches again", async () => {
    const user = userEvent.setup();
    const onUrlUpdate = renderControls();

    await user.click(screen.getByRole("button", { name: "Total pay" }));

    await waitFor(() => expect(onUrlUpdate).toHaveBeenCalled());
    expect(lastUpdate(onUrlUpdate).queryString).toBe("?comp=total");
    expect(lastUpdate(onUrlUpdate).options.shallow).toBe(false);
  });

  it("shows which toggle is on", () => {
    renderControls("?comp=total&period=monthly");

    expect(screen.getByRole("button", { name: "Total pay" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByRole("button", { name: "Monthly" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("names the population and lets you widen it", async () => {
    const user = userEvent.setup();
    const onUrlUpdate = renderControls();

    await user.click(
      screen.getByRole("button", { name: /Full-time · Active/ }),
    );
    await user.click(screen.getByRole("checkbox", { name: "Part-time" }));

    await waitFor(() => expect(onUrlUpdate).toHaveBeenCalled());
    expect(lastUpdate(onUrlUpdate).queryString).toBe(
      "?employment_type=FULL_TIME&employment_type=PART_TIME",
    );
  });

  it("lets a long population wrap at 360 px instead of overflowing", () => {
    renderControls(
      "?employment_type=FULL_TIME&employment_type=PART_TIME&employment_type=CONTRACTOR&status=ACTIVE&status=ON_LEAVE",
    );

    const chip = screen.getByRole("button", { name: /Change who is counted/ });
    expect(chip).toHaveClass("min-h-11", "text-left");
    expect(chip).not.toHaveClass("h-11");
  });

  it("keeps at least one employment type and one status", async () => {
    const user = userEvent.setup();
    renderControls();

    await user.click(
      screen.getByRole("button", { name: /Full-time · Active/ }),
    );

    expect(screen.getByRole("checkbox", { name: "Full-time" })).toBeDisabled();
    expect(screen.getByRole("checkbox", { name: "Active" })).toBeDisabled();
  });

  it("filters by country and department with the API's names", async () => {
    const user = userEvent.setup();
    const onUrlUpdate = renderControls();

    await user.selectOptions(
      screen.getByRole("combobox", { name: "Country" }),
      "Germany",
    );
    await waitFor(() => expect(onUrlUpdate).toHaveBeenCalled());
    expect(lastUpdate(onUrlUpdate).queryString).toBe("?country=DE");

    await user.selectOptions(
      screen.getByRole("combobox", { name: "Department" }),
      "Customer Success",
    );
    await waitFor(() =>
      expect(lastUpdate(onUrlUpdate).queryString).toBe(
        "?country=DE&department_id=4",
      ),
    );
  });

  it("goes back to every country", async () => {
    const user = userEvent.setup();
    const onUrlUpdate = renderControls("?country=DE");

    await user.selectOptions(
      screen.getByRole("combobox", { name: "Country" }),
      "All countries",
    );

    await waitFor(() => expect(onUrlUpdate).toHaveBeenCalled());
    expect(lastUpdate(onUrlUpdate).queryString).toBe("");
  });
});
