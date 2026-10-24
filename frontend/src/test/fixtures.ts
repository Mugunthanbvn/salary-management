import type { components } from "@/lib/api/schema";

type MeResponse = components["schemas"]["MeResponse"];
type Permission = components["schemas"]["Permission"];
type ReferenceData = components["schemas"]["ReferenceData"];
type EmployeeListItem = components["schemas"]["EmployeeListItem"];
type EmployeePage = components["schemas"]["EmployeePage"];
type EmployeeDetail = components["schemas"]["EmployeeDetail"];
type SalaryHistoryRecord = components["schemas"]["SalaryHistoryRecord"];
type Problem = components["schemas"]["Problem"];
type ValidationProblem = components["schemas"]["ValidationProblem"];

// Test data mirroring ROLE_PERMISSIONS in backend/src/salary_api/core/permissions.py.
// The UI never derives permissions from a role; it reads them from GET /auth/me.
export const HR_MANAGER_PERMISSIONS: Permission[] = [
  "EMPLOYEE_READ",
  "EMPLOYEE_WRITE",
  "SALARY_READ",
  "SALARY_WRITE",
  "INSIGHTS_READ",
  "EXPORT",
  "IMPORT",
  "ASK",
];

export const VIEWER_PERMISSIONS: Permission[] = [
  "EMPLOYEE_READ",
  "INSIGHTS_READ",
  "EXPORT",
  "ASK",
];

/** A GET /auth/me body for an HR manager with Ask on; override what the test is about. */
export function makeMe(overrides: Partial<MeResponse> = {}): MeResponse {
  return {
    user: {
      id: 2,
      email: "hr@acme.example",
      full_name: "Hema Iyer",
      role: "HR_MANAGER",
    },
    permissions: HR_MANAGER_PERMISSIONS,
    features: { ask: true },
    ...overrides,
  };
}

/** A viewer: employees and insights, never individual salaries. */
export function makeViewer(): MeResponse {
  return makeMe({
    user: {
      id: 3,
      email: "viewer@acme.example",
      full_name: "Farah Khan",
      role: "VIEWER",
    },
    permissions: VIEWER_PERMISSIONS,
  });
}

/** A small GET /reference body: five countries, two departments, three roles. */
export function makeReference(
  overrides: Partial<ReferenceData> = {},
): ReferenceData {
  return {
    countries: [
      { code: "FR", name: "France", default_currency: "EUR", is_active: true },
      { code: "DE", name: "Germany", default_currency: "EUR", is_active: true },
      { code: "IN", name: "India", default_currency: "INR", is_active: true },
      { code: "JP", name: "Japan", default_currency: "JPY", is_active: true },
      {
        code: "US",
        name: "United States",
        default_currency: "USD",
        is_active: true,
      },
    ],
    departments: [
      { id: 4, name: "Customer Success" },
      { id: 1, name: "Engineering" },
    ],
    job_roles: [
      {
        id: 3,
        title: "Backend Engineer",
        department_id: 1,
        family: "ENGINEERING",
      },
      {
        id: 17,
        title: "Customer Success Manager",
        department_id: 4,
        family: "CUSTOMER_SUCCESS",
      },
      {
        id: 5,
        title: "Software Engineer",
        department_id: 1,
        family: "ENGINEERING",
      },
    ],
    levels: [
      { code: "L1", label: "Associate" },
      { code: "L2", label: "Mid" },
      { code: "L3", label: "Senior" },
      { code: "L4", label: "Lead/Staff" },
      { code: "L5", label: "Principal" },
      { code: "L6", label: "Director" },
    ],
    employment_types: ["FULL_TIME", "PART_TIME", "CONTRACTOR"],
    currencies: [
      { code: "EUR", exponent: 2 },
      { code: "INR", exponent: 2 },
      { code: "JPY", exponent: 0 },
      { code: "USD", exponent: 2 },
    ],
    salary_change_reasons: [
      "HIRE",
      "PROMOTION",
      "MERIT",
      "MARKET_ADJUSTMENT",
      "CORRECTION",
    ],
    ...overrides,
  };
}

/** An employee as GET /employees lists them, seen by an HR manager (salaries shown). */
export function makeEmployeeListItem(
  overrides: Partial<EmployeeListItem> = {},
): EmployeeListItem {
  return {
    id: 2210,
    employee_code: "ACME-002210",
    first_name: "Lena",
    last_name: "Müller",
    email: "lena.mueller@acme.example",
    job_role: { id: 17, title: "Customer Success Manager" },
    department: { id: 4, name: "Customer Success" },
    level: "L2",
    employment_type: "FULL_TIME",
    country_code: "DE",
    status: "ACTIVE",
    hire_date: "2022-06-01",
    current_base: { amount_minor: 4_750_000, currency: "EUR" },
    current_total: { amount_minor: 5_182_000, currency: "EUR" },
    salary_masked: false,
    version: 3,
    ...overrides,
  };
}

/** The same employee as a viewer gets them: no salary, masked. */
export function makeMaskedListItem(
  overrides: Partial<EmployeeListItem> = {},
): EmployeeListItem {
  return makeEmployeeListItem({
    current_base: null,
    current_total: null,
    salary_masked: true,
    ...overrides,
  });
}

/** A GET /employees page of these items. */
export function makeEmployeePage(
  items: EmployeeListItem[] = [makeEmployeeListItem()],
  overrides: Partial<EmployeePage> = {},
): EmployeePage {
  return { items, page: 1, page_size: 25, total: items.length, ...overrides };
}

/** GET /employees/{id} for an HR manager: Lena Müller in Germany, with two components. */
export function makeEmployeeDetail(
  overrides: Partial<EmployeeDetail> = {},
): EmployeeDetail {
  return {
    ...makeEmployeeListItem(),
    termination_date: null,
    current_salary: {
      id: 9002,
      effective_date: "2025-04-01",
      reason: "MERIT",
      components: [
        {
          type: "ALLOWANCE",
          name: "Transport",
          amount: { amount_minor: 60_000, currency: "EUR" },
        },
        {
          type: "BONUS_TARGET",
          name: "Target bonus",
          amount: { amount_minor: 372_000, currency: "EUR" },
        },
      ],
    },
    ...overrides,
  };
}

/** The same employee as a viewer gets them: no salary, masked. */
export function makeMaskedDetail(
  overrides: Partial<EmployeeDetail> = {},
): EmployeeDetail {
  return makeEmployeeDetail({
    current_base: null,
    current_total: null,
    current_salary: null,
    salary_masked: true,
    ...overrides,
  });
}

/** One record of GET /employees/{id}/salary-history. */
export function makeHistoryRecord(
  overrides: Partial<SalaryHistoryRecord> = {},
): SalaryHistoryRecord {
  return {
    id: 9001,
    effective_date: "2022-06-01",
    reason: "HIRE",
    job_role: { id: 17, title: "Customer Success Manager" },
    level: "L2",
    base: { amount_minor: 4_500_000, currency: "EUR" },
    total: { amount_minor: 4_932_000, currency: "EUR" },
    components: [],
    base_change_pct: null,
    changed_by: null,
    note: null,
    created_at: "2026-10-20T10:00:00Z",
    ...overrides,
  };
}

/** A problem+json body with a glossary §5 slug. */
export function makeProblem(
  slug: string,
  status: number,
  overrides: Partial<Problem> = {},
): Problem {
  return {
    type: `https://acme.example/problems/${slug}`,
    title: slug,
    status,
    instance: "/api/v1/employees/2210",
    request_id: "req-123",
    ...overrides,
  };
}

type ImportJobReport = components["schemas"]["ImportJobReport"];
type ImportPreviewRow = components["schemas"]["ImportPreviewRow"];
type ImportRowError = components["schemas"]["ImportRowError"];

/** A valid row of a dry-run's preview: Ananya Rao, hired in India. */
export function makePreviewRow(
  overrides: Partial<ImportPreviewRow> = {},
): ImportPreviewRow {
  return {
    row: 2,
    employee_code: "ACME-010001",
    first_name: "Ananya",
    last_name: "Rao",
    email: "ananya.rao@acme.example",
    job_role: "Software Engineer",
    department: "Engineering",
    level: "L2",
    employment_type: "FULL_TIME",
    country_code: "IN",
    hire_date: "2026-09-01",
    salary_effective_date: "2026-09-01",
    base: { amount_minor: 150_000_000, currency: "INR" },
    total: { amount_minor: 162_000_000, currency: "INR" },
    ...overrides,
  };
}

/** One refused cell of a dry-run. */
export function makeRowError(
  overrides: Partial<ImportRowError> = {},
): ImportRowError {
  return {
    row: 12,
    column: "email",
    code: "duplicate_in_file",
    message: "Same email as row 4.",
    value: "a.rao@acme.example",
    ...overrides,
  };
}

/** A POST /imports (or GET /imports/{id}) dry-run with no errors: 3 rows, all valid. */
export function makeImportReport(
  overrides: Partial<ImportJobReport> = {},
): ImportJobReport {
  return {
    id: 31,
    status: "DRY_RUN",
    format: "CSV",
    filename: "q4-new-hires.csv",
    row_count: 3,
    valid_count: 3,
    error_count: 0,
    errors: [],
    errors_truncated: false,
    allowed_values: {},
    preview: [
      makePreviewRow(),
      makePreviewRow({
        row: 3,
        employee_code: "ACME-010002",
        first_name: "Lena",
        last_name: "Weber",
        email: "lena.weber@acme.example",
        country_code: "DE",
        base: { amount_minor: 5_200_000, currency: "EUR" },
        total: { amount_minor: 5_616_000, currency: "EUR" },
      }),
      makePreviewRow({
        row: 4,
        employee_code: "ACME-010003",
        first_name: "Taro",
        last_name: "Yamada",
        email: "taro.yamada@acme.example",
        country_code: "JP",
        base: { amount_minor: 4_500_000, currency: "JPY" },
        total: { amount_minor: 4_500_000, currency: "JPY" },
      }),
    ],
    created_at: "2026-10-24T10:45:00Z",
    expires_at: "2026-10-25T10:45:00Z",
    committed_at: null,
    ...overrides,
  };
}

/** A 422 `validation` problem listing these field errors. */
export function makeValidationProblem(
  errors: ValidationProblem["errors"],
): ValidationProblem {
  return {
    type: "https://acme.example/problems/validation",
    title: "Validation failed",
    status: 422,
    detail: `${errors.length} fields are invalid.`,
    instance: "/api/v1/employees/2210/salary-changes",
    request_id: "req-422",
    errors,
  };
}
