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

import { EmployeeActions } from "./employee-actions";

type EmployeeDetail = components["schemas"]["EmployeeDetail"];
type EmployeeUpdate = components["schemas"]["EmployeeUpdate"];
type TerminateRequest = components["schemas"]["TerminateRequest"];
type ReactivateRequest = components["schemas"]["ReactivateRequest"];
type Problem = components["schemas"]["Problem"];
type ValidationProblem = components["schemas"]["ValidationProblem"];

vi.mock("next/headers", () => ({ cookies: vi.fn() }));
vi.mock("next/cache", () => ({ revalidatePath: vi.fn() }));
const { refresh } = vi.hoisted(() => ({ refresh: vi.fn() }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh, push: vi.fn() }),
}));

const EMPLOYEE_URL = `${API_ORIGIN}/api/v1/employees/:id`;

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date("2026-10-24T09:00:00Z"));
  signedInRequest();
});

afterEach(() => {
  vi.useRealTimers();
});

async function open(
  button: string,
  employee: EmployeeDetail = makeEmployeeDetail(),
) {
  renderInApp(
    <>
      <EmployeeActions employee={employee} reference={makeReference()} />
      <Toaster />
    </>,
  );
  await userEvent.click(screen.getByRole("button", { name: button }));
  return screen.getByRole("dialog");
}

function conflict(url: string, method: "patch" | "post") {
  server.use(
    http[method]<never, never, Problem>(url, () =>
      HttpResponse.json(
        makeProblem("version-conflict", 409, {
          title: "Version conflict",
          current_version: 9,
        }),
        { status: 409 },
      ),
    ),
  );
}

async function expectConflict(dialog: HTMLElement, submit: string) {
  await userEvent.click(within(dialog).getByRole("button", { name: submit }));
  const alert = await within(dialog).findByRole("alert");
  expect(alert).toHaveTextContent(
    "This employee was changed by someone else. Reload to see their changes.",
  );
  await userEvent.click(within(alert).getByRole("button", { name: "Reload" }));
  expect(refresh).toHaveBeenCalled();
}

describe("Edit details", () => {
  it("starts from the current profile", async () => {
    const dialog = await open("Edit details");

    expect(dialog).toHaveAccessibleName("Edit Lena Müller's details");
    expect(
      within(dialog).getByRole("textbox", { name: "First name" }),
    ).toHaveValue("Lena");
    expect(
      within(dialog).getByRole("textbox", { name: "Last name" }),
    ).toHaveValue("Müller");
    expect(
      within(dialog).getByRole("textbox", { name: "Email" }),
    ).toHaveAttribute("type", "email");
    expect(
      within(dialog).getByRole("combobox", { name: "Employment type" }),
    ).toHaveValue("FULL_TIME");
  });

  it("sends only the changed fields, with the version it read", async () => {
    let body: EmployeeUpdate | null = null;
    server.use(
      http.patch<{ id: string }, EmployeeUpdate, EmployeeDetail>(
        EMPLOYEE_URL,
        async ({ request }) => {
          body = await request.json();
          return HttpResponse.json(makeEmployeeDetail({ version: 4 }));
        },
      ),
    );
    const dialog = await open("Edit details");

    const first = within(dialog).getByRole("textbox", { name: "First name" });
    await userEvent.clear(first);
    await userEvent.type(first, "Lene");
    await userEvent.selectOptions(
      within(dialog).getByRole("combobox", { name: "Employment type" }),
      "PART_TIME",
    );
    await userEvent.click(
      within(dialog).getByRole("button", { name: "Save details" }),
    );

    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(body).toEqual({
      version: 3,
      first_name: "Lene",
      employment_type: "PART_TIME",
    });
    expect(await screen.findByText("Details saved.")).toBeVisible();
  });

  it("closes without asking the API when nothing changed", async () => {
    const dialog = await open("Edit details");

    await userEvent.click(
      within(dialog).getByRole("button", { name: "Save details" }),
    );

    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  });

  it("shows the API's email error next to the email field", async () => {
    server.use(
      http.patch<never, never, ValidationProblem>(EMPLOYEE_URL, () =>
        HttpResponse.json(
          makeValidationProblem([
            {
              loc: ["body", "email"],
              code: "string_pattern_mismatch",
              message: "String should match pattern '^[^@\\s]+@[^@\\s]+$'",
            },
          ]),
          { status: 422 },
        ),
      ),
    );
    const dialog = await open("Edit details");

    const email = within(dialog).getByRole("textbox", { name: "Email" });
    await userEvent.clear(email);
    await userEvent.type(email, "lena-at-acme");
    await userEvent.click(
      within(dialog).getByRole("button", { name: "Save details" }),
    );

    await waitFor(() =>
      expect(email).toHaveAccessibleDescription(
        "String should match pattern '^[^@\\s]+@[^@\\s]+$'",
      ),
    );
  });

  it("says when the email belongs to someone else", async () => {
    server.use(
      http.patch<never, never, Problem>(EMPLOYEE_URL, () =>
        HttpResponse.json(
          makeProblem("duplicate", 409, {
            title: "Duplicate",
            detail:
              "The email jonas@acme.example is already in use by another employee.",
          }),
          { status: 409 },
        ),
      ),
    );
    const dialog = await open("Edit details");

    const email = within(dialog).getByRole("textbox", { name: "Email" });
    await userEvent.clear(email);
    await userEvent.type(email, "jonas@acme.example");
    await userEvent.click(
      within(dialog).getByRole("button", { name: "Save details" }),
    );

    await waitFor(() =>
      expect(email).toHaveAccessibleDescription(
        "The email jonas@acme.example is already in use by another employee.",
      ),
    );
  });

  it("explains a version conflict", async () => {
    conflict(EMPLOYEE_URL, "patch");
    const dialog = await open("Edit details");
    await userEvent.type(
      within(dialog).getByRole("textbox", { name: "Last name" }),
      "x",
    );

    await expectConflict(dialog, "Save details");
  });
});

describe("Terminate", () => {
  it("asks to confirm, with today's date, and sends the date and note", async () => {
    let body: TerminateRequest | null = null;
    server.use(
      http.post<{ id: string }, TerminateRequest, EmployeeDetail>(
        `${EMPLOYEE_URL}/terminate`,
        async ({ request }) => {
          body = await request.json();
          return HttpResponse.json(
            makeEmployeeDetail({ status: "TERMINATED" }),
          );
        },
      ),
    );
    const dialog = await open("Terminate");

    expect(dialog).toHaveAccessibleName("Terminate Lena Müller?");
    expect(within(dialog).getByLabelText("Last day")).toHaveValue("2026-10-24");
    await userEvent.type(
      within(dialog).getByRole("textbox", { name: "Note" }),
      "Resigned",
    );
    await userEvent.click(
      within(dialog).getByRole("button", { name: "Terminate" }),
    );

    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(body).toEqual({
      version: 3,
      termination_date: "2026-10-24",
      note: "Resigned",
    });
    expect(
      await screen.findByText("Lena Müller was terminated."),
    ).toBeVisible();
  });

  it("refuses a last day before the hire date, as the API would", async () => {
    const dialog = await open("Terminate");

    const date = within(dialog).getByLabelText("Last day");
    expect(date).toHaveAttribute("min", "2022-06-01");
    await userEvent.clear(date);
    await userEvent.type(date, "2021-12-31");
    await userEvent.click(
      within(dialog).getByRole("button", { name: "Terminate" }),
    );

    expect(date).toHaveAccessibleDescription(
      "The employee was hired on 1 Jun 2022.",
    );
    expect(screen.getByRole("dialog")).toBeVisible();
  });

  it("explains a version conflict", async () => {
    conflict(`${EMPLOYEE_URL}/terminate`, "post");
    const dialog = await open("Terminate");

    await expectConflict(dialog, "Terminate");
  });
});

describe("Reactivate", () => {
  const terminated = makeEmployeeDetail({
    status: "TERMINATED",
    termination_date: "2026-02-15",
    version: 7,
  });

  it("asks to confirm, then sends the version", async () => {
    let body: ReactivateRequest | null = null;
    server.use(
      http.post<{ id: string }, ReactivateRequest, EmployeeDetail>(
        `${EMPLOYEE_URL}/reactivate`,
        async ({ request }) => {
          body = await request.json();
          return HttpResponse.json(makeEmployeeDetail({ version: 8 }));
        },
      ),
    );
    const dialog = await open("Reactivate", terminated);

    expect(dialog).toHaveAccessibleName("Reactivate Lena Müller?");
    await userEvent.click(
      within(dialog).getByRole("button", { name: "Reactivate" }),
    );

    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(body).toEqual({ version: 7 });
    expect(
      await screen.findByText("Lena Müller was reactivated."),
    ).toBeVisible();
  });

  it("explains a version conflict", async () => {
    conflict(`${EMPLOYEE_URL}/reactivate`, "post");
    const dialog = await open("Reactivate", terminated);

    await expectConflict(dialog, "Reactivate");
  });
});
