import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { Toaster } from "@/components/ui/sonner";
import { API_ORIGIN } from "@/lib/api/origin";
import type { components } from "@/lib/api/schema";
import {
  makeEmployeeDetail,
  makeProblem,
  makeReference,
  makeValidationProblem,
} from "@/test/fixtures";
import { server } from "@/test/msw/server";
import { renderInApp } from "@/test/render";
import { signedInRequest } from "@/test/server";

import { NewEmployeeForm } from "./new-employee-form";

type EmployeeCreate = components["schemas"]["EmployeeCreate"];
type EmployeeDetail = components["schemas"]["EmployeeDetail"];
type Problem = components["schemas"]["Problem"];
type ValidationProblem = components["schemas"]["ValidationProblem"];

vi.mock("next/headers", () => ({ cookies: vi.fn() }));
vi.mock("next/cache", () => ({ revalidatePath: vi.fn() }));
const { push } = vi.hoisted(() => ({ push: vi.fn() }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn(), push }),
}));

const EMPLOYEES_URL = `${API_ORIGIN}/api/v1/employees`;

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date("2026-10-24T09:00:00Z"));
  signedInRequest();
});

afterEach(() => {
  vi.useRealTimers();
});

function renderForm() {
  renderInApp(
    <>
      <NewEmployeeForm reference={makeReference()} />
      <Toaster />
    </>,
  );
  return screen.getByRole("form", { name: "New employee" });
}

async function fillRequired(form: HTMLElement) {
  const type = (name: string, text: string) =>
    userEvent.type(within(form).getByRole("textbox", { name }), text);
  await type("First name", "Lena");
  await type("Last name", "Müller");
  await type("Email", "lena.mueller@acme.example");
  await userEvent.selectOptions(
    within(form).getByRole("combobox", { name: "Job role" }),
    "17",
  );
  await userEvent.selectOptions(
    within(form).getByRole("combobox", { name: "Level" }),
    "L2",
  );
  await userEvent.selectOptions(
    within(form).getByRole("combobox", { name: "Country" }),
    "DE",
  );
  await type("Starting base pay (EUR a year)", "54,000");
}

describe("NewEmployeeForm", () => {
  it("asks who they are, what their job is and what they will be paid", () => {
    renderForm();

    for (const question of [
      "Who are they?",
      "What is their job?",
      "What will they be paid?",
    ]) {
      expect(screen.getByRole("region", { name: question })).toBeVisible();
    }
    expect(screen.getByLabelText("Hire date")).toHaveValue("2026-10-24");
    expect(
      screen.getByRole("combobox", { name: "Employment type" }),
    ).toHaveValue("FULL_TIME");
  });

  it("pays in the chosen country's currency, shown but not editable", async () => {
    const form = renderForm();

    expect(
      within(form).getByText("Choose a country to see the currency."),
    ).toBeVisible();
    await userEvent.selectOptions(
      within(form).getByRole("combobox", { name: "Country" }),
      "JP",
    );

    expect(
      within(form).getByText("Paid in JPY, the currency of Japan."),
    ).toBeVisible();
    expect(
      within(form).getByRole("textbox", {
        name: "Starting base pay (JPY a year)",
      }),
    ).toHaveAttribute("inputmode", "decimal");
    expect(
      within(form).queryByRole("combobox", { name: /currency/i }),
    ).toBeNull();
  });

  it("adds the employee with their first salary in minor units, then opens their page", async () => {
    let body: EmployeeCreate | null = null;
    server.use(
      http.post<never, EmployeeCreate, EmployeeDetail>(
        EMPLOYEES_URL,
        async ({ request }) => {
          body = await request.json();
          return HttpResponse.json(makeEmployeeDetail({ id: 10001 }), {
            status: 201,
          });
        },
      ),
    );
    const form = renderForm();
    await fillRequired(form);
    await userEvent.click(
      within(form).getByRole("button", { name: "Add a component" }),
    );
    const row = within(form).getByRole("group", { name: "Component 1" });
    await userEvent.type(
      within(row).getByRole("textbox", { name: "Name" }),
      "Transport",
    );
    await userEvent.type(
      within(row).getByRole("textbox", { name: "Amount (EUR a year)" }),
      "600",
    );

    await userEvent.click(
      within(form).getByRole("button", { name: "Add employee" }),
    );

    await waitFor(() => expect(push).toHaveBeenCalledWith("/employees/10001"));
    expect(body).toEqual({
      first_name: "Lena",
      last_name: "Müller",
      email: "lena.mueller@acme.example",
      job_role_id: 17,
      level: "L2",
      employment_type: "FULL_TIME",
      country_code: "DE",
      hire_date: "2026-10-24",
      salary: {
        base_minor: 5_400_000,
        components: [
          { type: "ALLOWANCE", name: "Transport", amount_minor: 60_000 },
        ],
      },
    });
    expect(await screen.findByText("Lena Müller was added.")).toBeVisible();
  });

  it("asks for what is missing before sending anything", async () => {
    const form = renderForm();

    await userEvent.click(
      within(form).getByRole("button", { name: "Add employee" }),
    );

    expect(
      within(form).getByRole("combobox", { name: "Country" }),
    ).toHaveAccessibleDescription("Choose a country");
    expect(
      within(form).getByRole("combobox", { name: "Job role" }),
    ).toHaveAccessibleDescription("Choose a job role");
    expect(
      within(form).getByRole("textbox", { name: "First name" }),
    ).toHaveAccessibleDescription("Enter a first name");
  });

  it("shows the API's field errors next to their fields", async () => {
    server.use(
      http.post<never, never, ValidationProblem>(EMPLOYEES_URL, () =>
        HttpResponse.json(
          makeValidationProblem([
            {
              loc: ["body", "hire_date"],
              code: "future_date",
              message: "The hire date cannot be in the future.",
            },
            {
              loc: ["body", "salary", "base_minor"],
              code: "less_than_equal",
              message: "Input should be less than or equal to 999999999999999",
            },
          ]),
          { status: 422 },
        ),
      ),
    );
    const form = renderForm();
    await fillRequired(form);

    await userEvent.click(
      within(form).getByRole("button", { name: "Add employee" }),
    );

    await waitFor(() =>
      expect(
        within(form).getByLabelText("Hire date"),
      ).toHaveAccessibleDescription("The hire date cannot be in the future."),
    );
    expect(
      within(form).getByRole("textbox", {
        name: "Starting base pay (EUR a year)",
      }),
    ).toHaveAccessibleDescription(
      "Input should be less than or equal to 999999999999999",
    );
    expect(push).not.toHaveBeenCalled();
  });

  it("says when the email or code is already taken", async () => {
    server.use(
      http.post<never, never, Problem>(EMPLOYEES_URL, () =>
        HttpResponse.json(
          makeProblem("duplicate", 409, {
            title: "Duplicate",
            detail:
              "The email lena.mueller@acme.example is already in use by another employee.",
          }),
          { status: 409 },
        ),
      ),
    );
    const form = renderForm();
    await fillRequired(form);

    await userEvent.click(
      within(form).getByRole("button", { name: "Add employee" }),
    );

    expect(await within(form).findByRole("alert")).toHaveTextContent(
      "The email lena.mueller@acme.example is already in use by another employee.",
    );
  });
});
