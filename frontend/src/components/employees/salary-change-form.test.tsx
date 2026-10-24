import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { revalidatePath } from "next/cache";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { Toaster } from "@/components/ui/sonner";
import { API_ORIGIN } from "@/lib/api/origin";
import type { components } from "@/lib/api/schema";
import {
  makeEmployeeDetail,
  makeHistoryRecord,
  makeProblem,
  makeReference,
  makeValidationProblem,
} from "@/test/fixtures";
import { server } from "@/test/msw/server";
import { renderInApp } from "@/test/render";
import { signedInRequest } from "@/test/server";

import { EmployeeActions } from "./employee-actions";

type EmployeeDetail = components["schemas"]["EmployeeDetail"];
type SalaryChange = components["schemas"]["SalaryChange"];
type SalaryChangeRequest = components["schemas"]["SalaryChangeRequest"];
type Problem = components["schemas"]["Problem"];
type ValidationProblem = components["schemas"]["ValidationProblem"];

vi.mock("next/headers", () => ({ cookies: vi.fn() }));
vi.mock("next/cache", () => ({ revalidatePath: vi.fn() }));
const { refresh } = vi.hoisted(() => ({ refresh: vi.fn() }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh, push: vi.fn() }),
}));

const CHANGES_URL = `${API_ORIGIN}/api/v1/employees/:id/salary-changes`;
const reference = makeReference();

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date("2026-10-24T09:00:00Z"));
  signedInRequest();
});

afterEach(() => {
  vi.useRealTimers();
});

async function openForm(employee: EmployeeDetail = makeEmployeeDetail()) {
  renderInApp(
    <>
      <EmployeeActions employee={employee} reference={reference} />
      <Toaster />
    </>,
  );
  const [headerButton] = screen.getAllByRole("button", {
    name: "Record salary change",
  });
  await userEvent.click(headerButton!);
  return screen.getByRole("dialog", { name: "Record a salary change" });
}

/** Records the request body; answers 201 with the new record. */
function acceptChange() {
  const seen: { body: SalaryChangeRequest | null } = { body: null };
  server.use(
    http.post<{ id: string }, SalaryChangeRequest, SalaryChange>(
      CHANGES_URL,
      async ({ request }) => {
        seen.body = await request.json();
        return HttpResponse.json(
          {
            record: makeHistoryRecord({ reason: "MERIT" }),
            employee_version: 4,
          },
          { status: 201 },
        );
      },
    ),
  );
  return seen;
}

function field(form: HTMLElement, name: string | RegExp) {
  return within(form).getByRole("textbox", { name });
}

describe("Record salary change", () => {
  it("starts from today, a merit raise, and the current pay", async () => {
    const form = await openForm();

    expect(within(form).getByLabelText("Effective date")).toHaveValue(
      "2026-10-24",
    );
    const reason = within(form).getByRole("combobox", { name: "Reason" });
    expect(reason).toHaveValue("MERIT");
    expect(
      within(reason)
        .getAllByRole("option")
        .map((option) => option.textContent),
    ).not.toContain("Hired");
    const base = field(form, "New base pay (EUR a year)");
    expect(base).toHaveValue("47500");
    expect(base).toHaveAttribute("inputmode", "decimal");
    const rows = within(form).getAllByRole("group", { name: /^Component \d/ });
    expect(rows).toHaveLength(2);
    expect(within(rows[0]!).getByRole("textbox", { name: "Name" })).toHaveValue(
      "Transport",
    );
    expect(
      within(rows[1]!).getByRole("textbox", { name: "Amount (EUR a year)" }),
    ).toHaveValue("3720");
  });

  it("sends the base and components in minor units, then closes and confirms", async () => {
    const seen = acceptChange();
    const form = await openForm();

    await userEvent.clear(field(form, "New base pay (EUR a year)"));
    await userEvent.type(field(form, "New base pay (EUR a year)"), "50,000.50");
    await userEvent.click(
      within(form).getByRole("button", { name: "Remove Target bonus" }),
    );
    await userEvent.click(
      within(form).getByRole("button", { name: "Add a component" }),
    );
    const added = within(form)
      .getAllByRole("group", { name: /^Component \d/ })
      .at(-1)!;
    await userEvent.type(
      within(added).getByRole("textbox", { name: "Name" }),
      "Phone",
    );
    await userEvent.type(
      within(added).getByRole("textbox", { name: "Amount (EUR a year)" }),
      "240",
    );
    await userEvent.type(
      within(form).getByRole("textbox", { name: "Note" }),
      "Cycle 2026",
    );
    await userEvent.click(
      within(form).getByRole("button", { name: "Record salary change" }),
    );

    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(seen.body).toEqual({
      version: 3,
      effective_date: "2026-10-24",
      reason: "MERIT",
      base_minor: 5_000_050,
      components: [
        { type: "ALLOWANCE", name: "Transport", amount_minor: 60_000 },
        { type: "ALLOWANCE", name: "Phone", amount_minor: 24_000 },
      ],
      note: "Cycle 2026",
    });
    expect(await screen.findByText("Salary change recorded.")).toBeVisible();
    expect(revalidatePath).toHaveBeenCalledWith("/employees/2210");
  });

  it.each([
    { currency: "EUR", country: "DE", typed: "12.345", minor: null },
    { currency: "JPY", country: "JP", typed: "6000000.5", minor: null },
    { currency: "JPY", country: "JP", typed: "6,000,000", minor: 6_000_000 },
  ])(
    "reads $typed $currency with the currency's decimals",
    async ({ currency, country, typed, minor }) => {
      const seen = acceptChange();
      const employee = makeEmployeeDetail({
        country_code: country,
        current_base: { amount_minor: 5_000_000, currency },
        current_total: { amount_minor: 5_000_000, currency },
        current_salary: {
          id: 1,
          effective_date: "2025-04-01",
          reason: "MERIT",
          components: [],
        },
      });
      const form = await openForm(employee);

      const base = field(form, `New base pay (${currency} a year)`);
      await userEvent.clear(base);
      await userEvent.type(base, typed);
      await userEvent.click(
        within(form).getByRole("button", { name: "Record salary change" }),
      );

      if (minor === null) {
        const message = `${typed} has more decimals than ${currency} allows`;
        expect(within(form).getByText(message)).toBeVisible();
        expect(base).toHaveAccessibleDescription(message);
        expect(seen.body).toBeNull();
      } else {
        await waitFor(() => expect(seen.body?.base_minor).toBe(minor));
      }
    },
  );

  it("sends a promotion's new level, and a move's new country in its currency", async () => {
    const seen = acceptChange();
    const form = await openForm();

    await userEvent.selectOptions(
      within(form).getByRole("combobox", { name: "Reason" }),
      "PROMOTION",
    );
    await userEvent.selectOptions(
      within(form).getByRole("combobox", { name: "New level" }),
      "L3",
    );
    await userEvent.selectOptions(
      within(form).getByRole("combobox", { name: "New country" }),
      "IN",
    );

    expect(within(form).getByText(/pay will be in INR/)).toBeVisible();
    const base = field(form, "New base pay (INR a year)");
    await userEvent.clear(base);
    await userEvent.type(base, "21,60,000");
    for (const row of within(form).getAllByRole("group", {
      name: /^Component \d/,
    })) {
      await userEvent.click(
        within(row).getByRole("button", { name: /^Remove/ }),
      );
    }
    await userEvent.click(
      within(form).getByRole("button", { name: "Record salary change" }),
    );

    await waitFor(() => expect(seen.body).not.toBeNull());
    expect(seen.body).toMatchObject({
      reason: "PROMOTION",
      level: "L3",
      country_code: "IN",
      base_minor: 216_000_000,
      components: [],
    });
    expect(seen.body).not.toHaveProperty("job_role_id");
  });

  it("shows the API's field errors next to their fields", async () => {
    server.use(
      http.post<never, never, ValidationProblem>(CHANGES_URL, () =>
        HttpResponse.json(
          makeValidationProblem([
            {
              loc: ["body", "effective_date"],
              code: "before_latest_record",
              message: "The latest salary record is effective 2025-04-01.",
            },
            {
              loc: ["body", "components", 1, "amount_minor"],
              code: "less_than_equal",
              message: "Input should be less than or equal to 999999999999999",
            },
            {
              loc: ["body", "reason"],
              code: "not_a_promotion",
              message:
                "A promotion needs a higher level or a different job role.",
            },
          ]),
          { status: 422 },
        ),
      ),
    );
    const form = await openForm();

    await userEvent.click(
      within(form).getByRole("button", { name: "Record salary change" }),
    );

    expect(
      await within(form).findByLabelText("Effective date"),
    ).toHaveAccessibleDescription(
      "The latest salary record is effective 2025-04-01.",
    );
    expect(
      within(form).getByRole("combobox", { name: "Reason" }),
    ).toHaveAccessibleDescription(
      "A promotion needs a higher level or a different job role.",
    );
    const second = within(form).getAllByRole("group", {
      name: /^Component \d/,
    })[1]!;
    expect(
      within(second).getByRole("textbox", { name: "Amount (EUR a year)" }),
    ).toHaveAccessibleDescription(
      "Input should be less than or equal to 999999999999999",
    );
    expect(screen.getByRole("dialog")).toBeVisible();
  });

  it("explains a version conflict and reloads the page on request", async () => {
    server.use(
      http.post<never, never, Problem>(CHANGES_URL, () =>
        HttpResponse.json(
          makeProblem("version-conflict", 409, {
            title: "Version conflict",
            current_version: 5,
          }),
          { status: 409 },
        ),
      ),
    );
    const form = await openForm();

    await userEvent.click(
      within(form).getByRole("button", { name: "Record salary change" }),
    );

    const alert = await within(form).findByRole("alert");
    expect(alert).toHaveTextContent(
      "This employee was changed by someone else. Reload to see their changes.",
    );
    await userEvent.click(
      within(alert).getByRole("button", { name: "Reload" }),
    );

    expect(refresh).toHaveBeenCalled();
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  });

  it("opens full screen on a phone, with the title and the button always in view", async () => {
    const form = await openForm();

    expect(form.querySelector("[data-slot=dialog-header]")).toHaveClass(
      "sticky",
      "top-0",
    );
    expect(form.querySelector("[data-slot=dialog-footer]")).toHaveClass(
      "sticky",
      "bottom-0",
    );
  });
});
