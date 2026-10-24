// @vitest-environment node
import { http, HttpResponse } from "msw";
import { revalidatePath } from "next/cache";
import { describe, expect, it, vi } from "vitest";

import { API_ORIGIN } from "@/lib/api/origin";
import type { components } from "@/lib/api/schema";
import {
  makeEmployeeDetail,
  makeHistoryRecord,
  makeProblem,
  makeValidationProblem,
} from "@/test/fixtures";
import { server } from "@/test/msw/server";
import { signedInRequest } from "@/test/server";

import {
  createEmployee,
  reactivateEmployee,
  recordSalaryChange,
  terminateEmployee,
  updateEmployee,
} from "./actions";

type SalaryChange = components["schemas"]["SalaryChange"];
type SalaryChangeRequest = components["schemas"]["SalaryChangeRequest"];
type EmployeeDetail = components["schemas"]["EmployeeDetail"];
type EmployeeCreate = components["schemas"]["EmployeeCreate"];
type EmployeeUpdate = components["schemas"]["EmployeeUpdate"];
type TerminateRequest = components["schemas"]["TerminateRequest"];
type ReactivateRequest = components["schemas"]["ReactivateRequest"];
type Problem = components["schemas"]["Problem"];
type ValidationProblem = components["schemas"]["ValidationProblem"];

vi.mock("next/headers", () => ({ cookies: vi.fn() }));
vi.mock("next/cache", () => ({ revalidatePath: vi.fn() }));

const EMPLOYEE_URL = `${API_ORIGIN}/api/v1/employees/:id`;

const change: SalaryChangeRequest = {
  version: 3,
  effective_date: "2026-10-01",
  reason: "MERIT",
  base_minor: 5_000_000,
  components: [{ type: "ALLOWANCE", name: "Transport", amount_minor: 60_000 }],
  note: "Annual cycle",
};

describe("recordSalaryChange", () => {
  it("posts the change as the signed-in person and refreshes the pages that show it", async () => {
    signedInRequest("jwt-hr");
    let seen: {
      id: string;
      body: SalaryChangeRequest;
      auth: string | null;
    } | null = null;
    server.use(
      http.post<{ id: string }, SalaryChangeRequest, SalaryChange>(
        `${EMPLOYEE_URL}/salary-changes`,
        async ({ params, request }) => {
          seen = {
            id: params.id,
            body: await request.json(),
            auth: request.headers.get("Authorization"),
          };
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

    const result = await recordSalaryChange(2210, change);

    expect(result).toMatchObject({ ok: true, data: { employee_version: 4 } });
    expect(seen).toEqual({ id: "2210", body: change, auth: "Bearer jwt-hr" });
    expect(revalidatePath).toHaveBeenCalledWith("/employees/2210");
    expect(revalidatePath).toHaveBeenCalledWith("/employees");
  });

  it("returns a version conflict as plain data, with the current version, and refreshes nothing", async () => {
    signedInRequest();
    server.use(
      http.post<never, never, Problem>(`${EMPLOYEE_URL}/salary-changes`, () =>
        HttpResponse.json(
          makeProblem("version-conflict", 409, {
            title: "Version conflict",
            current_version: 5,
          }),
          { status: 409 },
        ),
      ),
    );

    const result = await recordSalaryChange(2210, change);

    expect(result).toEqual({
      ok: false,
      problem: expect.objectContaining({
        slug: "version-conflict",
        currentVersion: 5,
        requestId: "req-123",
      }) as unknown,
    });
    expect(revalidatePath).not.toHaveBeenCalled();
  });

  it("returns the API's field errors", async () => {
    signedInRequest();
    server.use(
      http.post<never, never, ValidationProblem>(
        `${EMPLOYEE_URL}/salary-changes`,
        () =>
          HttpResponse.json(
            makeValidationProblem([
              {
                loc: ["body", "effective_date"],
                code: "future_date",
                message: "A salary change cannot take effect in the future.",
              },
            ]),
            { status: 422 },
          ),
      ),
    );

    const result = await recordSalaryChange(2210, change);

    expect(result.ok).toBe(false);
    expect(!result.ok && result.problem.errors[0]?.code).toBe("future_date");
  });

  it("says so when the API can't be reached", async () => {
    signedInRequest();
    server.use(
      http.post(`${EMPLOYEE_URL}/salary-changes`, () => HttpResponse.error()),
    );

    const result = await recordSalaryChange(2210, change);

    expect(result).toEqual({
      ok: false,
      problem: expect.objectContaining({
        title: "Couldn't reach ACME Pay",
        status: 503,
      }) as unknown,
    });
  });

  it("refuses an id that is not a whole positive number, without calling the API", async () => {
    signedInRequest();

    const result = await recordSalaryChange(-1, change);

    expect(result).toMatchObject({ ok: false, problem: { slug: "not-found" } });
  });
});

describe("the other employee changes", () => {
  it("updateEmployee patches the profile with its version", async () => {
    signedInRequest();
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

    const result = await updateEmployee(2210, {
      version: 3,
      first_name: "Lene",
    });

    expect(result).toMatchObject({ ok: true, data: { version: 4 } });
    expect(body).toEqual({ version: 3, first_name: "Lene" });
    expect(revalidatePath).toHaveBeenCalledWith("/employees/2210");
  });

  it("terminateEmployee posts the date and note", async () => {
    signedInRequest();
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

    const result = await terminateEmployee(2210, {
      version: 3,
      termination_date: "2026-10-31",
      note: "Resigned",
    });

    expect(result).toMatchObject({ ok: true, data: { status: "TERMINATED" } });
    expect(body).toEqual({
      version: 3,
      termination_date: "2026-10-31",
      note: "Resigned",
    });
  });

  it("reactivateEmployee posts the version", async () => {
    signedInRequest();
    let body: ReactivateRequest | null = null;
    server.use(
      http.post<{ id: string }, ReactivateRequest, EmployeeDetail>(
        `${EMPLOYEE_URL}/reactivate`,
        async ({ request }) => {
          body = await request.json();
          return HttpResponse.json(makeEmployeeDetail());
        },
      ),
    );

    const result = await reactivateEmployee(2210, { version: 4 });

    expect(result.ok).toBe(true);
    expect(body).toEqual({ version: 4 });
  });

  it("createEmployee posts the new hire and refreshes the directory", async () => {
    signedInRequest();
    const hire: EmployeeCreate = {
      first_name: "Lena",
      last_name: "Müller",
      email: "lena.mueller@acme.example",
      job_role_id: 17,
      level: "L2",
      employment_type: "FULL_TIME",
      country_code: "DE",
      hire_date: "2026-09-01",
      salary: { base_minor: 5_400_000, components: [] },
    };
    let body: EmployeeCreate | null = null;
    server.use(
      http.post<never, EmployeeCreate, EmployeeDetail>(
        `${API_ORIGIN}/api/v1/employees`,
        async ({ request }) => {
          body = await request.json();
          return HttpResponse.json(makeEmployeeDetail({ id: 10001 }), {
            status: 201,
          });
        },
      ),
    );

    const result = await createEmployee(hire);

    expect(result).toMatchObject({ ok: true, data: { id: 10001 } });
    expect(body).toEqual(hire);
    expect(revalidatePath).toHaveBeenCalledWith("/employees");
  });
});
