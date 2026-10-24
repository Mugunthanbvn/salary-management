"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useId, useState, useTransition, type ReactNode } from "react";
import { toast } from "sonner";

import { createEmployee } from "@/app/(app)/employees/actions";
import { MarginNote, Section } from "@/components/print";
import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  NativeSelect,
  NativeSelectOption,
} from "@/components/ui/native-select";
import { Textarea } from "@/components/ui/textarea";
import { fieldErrors, type PlainProblem } from "@/lib/api/action-result";
import type { components } from "@/lib/api/schema";
import { todayIso } from "@/lib/dates";
import { EMPLOYMENT_TYPE_LABELS, EMPLOYMENT_TYPES } from "@/lib/labels";
import { toMinorUnits } from "@/lib/money-input";

import {
  ComponentsEditor,
  isComponentError,
  toComponentsIn,
  type ComponentRow,
} from "./components-editor";
import {
  FieldError,
  FormProblem,
  invalidProps,
  unmatchedErrors,
} from "./form-dialog";
import { exponentOf } from "./format";

type ReferenceData = components["schemas"]["ReferenceData"];
type EmployeeCreate = components["schemas"]["EmployeeCreate"];
type EmploymentType = components["schemas"]["EmploymentType"];
type Level = components["schemas"]["Level"];

const FIELDS = new Set([
  "first_name",
  "last_name",
  "email",
  "employee_code",
  "job_role_id",
  "level",
  "employment_type",
  "country_code",
  "hire_date",
  "salary.base_minor",
  "salary.note",
]);

/**
 * A new hire and their first salary, created together (POST /employees, docs/07 §6.2).
 * The salary is always in the country's currency, so the currency is shown, not chosen.
 * The API checks every rule; the form only asks for what is missing and reads amounts.
 */
export function NewEmployeeForm({ reference }: { reference: ReferenceData }) {
  const id = useId();
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [today] = useState(todayIso);
  const [values, setValues] = useState({
    first_name: "",
    last_name: "",
    email: "",
    employee_code: "",
    job_role_id: "",
    level: "",
    employment_type: "FULL_TIME" as EmploymentType,
    country_code: "",
    hire_date: today,
    base: "",
    note: "",
  });
  const [rows, setRows] = useState<ComponentRow[]>([]);
  const [clientErrors, setClientErrors] = useState<Record<string, string>>({});
  const [problem, setProblem] = useState<PlainProblem | null>(null);

  const set = (key: keyof typeof values) => (value: string) =>
    setValues((current) => ({ ...current, [key]: value }));
  const country = reference.countries.find(
    (c) => c.code === values.country_code,
  );
  const currency = country?.default_currency ?? null;
  const exponent = currency ? exponentOf(currency, reference) : null;
  const errors = { ...fieldErrors(problem), ...clientErrors };
  const unmatched = unmatchedErrors(
    errors,
    (key) => FIELDS.has(key) || isComponentError(key, "salary.components"),
  );

  function submit() {
    const next: Record<string, string> = {};
    const required: [keyof typeof values, string][] = [
      ["first_name", "Enter a first name"],
      ["last_name", "Enter a last name"],
      ["email", "Enter a work email"],
      ["job_role_id", "Choose a job role"],
      ["level", "Choose a level"],
      ["country_code", "Choose a country"],
      ["hire_date", "Enter the hire date"],
    ];
    for (const [key, message] of required) {
      if (!values[key].trim()) next[key] = message;
    }
    let baseMinor: number | null = null;
    let list = { components: [] as EmployeeCreate["salary"]["components"] };
    if (currency && exponent !== null) {
      const base = toMinorUnits(values.base, currency, exponent);
      if (base.ok) baseMinor = base.minor;
      else next["salary.base_minor"] = base.message;
      const converted = toComponentsIn(
        rows,
        currency,
        exponent,
        "salary.components",
      );
      Object.assign(next, converted.errors);
      list = converted;
    } else {
      next["salary.base_minor"] = "Choose a country first";
    }
    setClientErrors(next);
    setProblem(null);
    if (Object.keys(next).length || baseMinor === null) return;

    const body: EmployeeCreate = {
      ...(values.employee_code.trim()
        ? { employee_code: values.employee_code.trim() }
        : {}),
      first_name: values.first_name.trim(),
      last_name: values.last_name.trim(),
      email: values.email.trim(),
      job_role_id: Number(values.job_role_id),
      level: values.level as Level,
      employment_type: values.employment_type,
      country_code: values.country_code,
      hire_date: values.hire_date,
      salary: {
        // Always the country's; sent so the API confirms what the amounts were typed in.
        currency: currency ?? undefined,
        base_minor: baseMinor,
        components: list.components,
        ...(values.note.trim() ? { note: values.note.trim() } : {}),
      },
    };
    startTransition(async () => {
      const result = await createEmployee(body);
      if (result.ok) {
        toast.success(`${body.first_name} ${body.last_name} was added.`);
        router.push(`/employees/${result.data.id}`);
      } else {
        setProblem(result.problem);
      }
    });
  }

  const field = (
    key: keyof typeof values,
    label: string,
    input: (props: { id: string; describedBy: object }) => ReactNode,
    hint?: string,
  ) => {
    const fieldId = `${id}-${key}`;
    const errorKey =
      key === "base"
        ? "salary.base_minor"
        : key === "note"
          ? "salary.note"
          : key;
    const message = errors[errorKey];
    return (
      <div className="flex min-w-0 flex-col gap-2">
        <Label htmlFor={fieldId}>{label}</Label>
        {input({
          id: fieldId,
          describedBy: invalidProps(`${fieldId}-error`, message),
        })}
        <FieldError id={`${fieldId}-error`} message={message} />
        {hint && !message ? <p className="text-sm text-ink-2">{hint}</p> : null}
      </div>
    );
  };
  const text = (
    key: keyof typeof values,
    label: string,
    type = "text",
    hint?: string,
  ) =>
    field(
      key,
      label,
      ({ id: fieldId, describedBy }) => (
        <Input
          id={fieldId}
          type={type}
          autoComplete="off"
          value={values[key]}
          onChange={(event) => set(key)(event.target.value)}
          {...describedBy}
        />
      ),
      hint,
    );
  const select = (
    key: keyof typeof values,
    label: string,
    options: { value: string; label: string }[],
    placeholder?: string,
  ) =>
    field(key, label, ({ id: fieldId, describedBy }) => (
      <NativeSelect
        id={fieldId}
        value={values[key]}
        onChange={(event) => set(key)(event.target.value)}
        {...describedBy}
      >
        {placeholder ? (
          <NativeSelectOption value="" disabled>
            {placeholder}
          </NativeSelectOption>
        ) : null}
        {options.map((option) => (
          <NativeSelectOption key={option.value} value={option.value}>
            {option.label}
          </NativeSelectOption>
        ))}
      </NativeSelect>
    ));

  return (
    <form
      aria-label="New employee"
      noValidate
      onSubmit={(event) => {
        event.preventDefault();
        submit();
      }}
    >
      <div className="pt-6">
        <FormProblem
          problem={problem}
          unmatched={unmatched}
          onReload={() => router.refresh()}
        />
      </div>
      <Section question="Who are they?">
        <div className="grid max-w-[640px] gap-5 sm:grid-cols-2">
          {text("first_name", "First name")}
          {text("last_name", "Last name")}
          <div className="sm:col-span-2">{text("email", "Email", "email")}</div>
          {text(
            "employee_code",
            "Employee code",
            "text",
            "Leave empty to use the next free code.",
          )}
        </div>
      </Section>
      <Section question="What is their job?">
        <div className="grid max-w-[640px] gap-5 sm:grid-cols-2">
          <div className="sm:col-span-2">
            {select(
              "job_role_id",
              "Job role",
              reference.job_roles.map((r) => ({
                value: String(r.id),
                label: r.title,
              })),
              "Choose a job role",
            )}
          </div>
          {select(
            "level",
            "Level",
            reference.levels.map((l) => ({
              value: l.code,
              label: `${l.code} ${l.label}`,
            })),
            "Choose a level",
          )}
          {select(
            "employment_type",
            "Employment type",
            EMPLOYMENT_TYPES.map((t) => ({
              value: t,
              label: EMPLOYMENT_TYPE_LABELS[t],
            })),
          )}
          {select(
            "country_code",
            "Country",
            reference.countries
              .filter((c) => c.is_active)
              .map((c) => ({ value: c.code, label: c.name })),
            "Choose a country",
          )}
          {field("hire_date", "Hire date", ({ id: fieldId, describedBy }) => (
            <Input
              id={fieldId}
              type="date"
              max={today}
              value={values.hire_date}
              onChange={(event) => set("hire_date")(event.target.value)}
              {...describedBy}
            />
          ))}
        </div>
      </Section>
      <Section question="What will they be paid?">
        <div className="flex max-w-[640px] flex-col gap-5">
          <MarginNote>
            {country && currency
              ? `Paid in ${currency}, the currency of ${country.name}.`
              : "Choose a country to see the currency."}
          </MarginNote>
          <div className="sm:max-w-xs">
            {field(
              "base",
              `Starting base pay (${currency ?? "local currency"} a year)`,
              ({ id: fieldId, describedBy }) => (
                <Input
                  id={fieldId}
                  inputMode="decimal"
                  autoComplete="off"
                  value={values.base}
                  onChange={(event) => set("base")(event.target.value)}
                  className="font-serif text-[19px]"
                  {...describedBy}
                />
              ),
            )}
          </div>
          <ComponentsEditor
            rows={rows}
            onChange={setRows}
            currency={currency ?? "local currency"}
            errors={errors}
            prefix="salary.components"
          />
          {field("note", "Note", ({ id: fieldId, describedBy }) => (
            <Textarea
              id={fieldId}
              value={values.note}
              maxLength={500}
              onChange={(event) => set("note")(event.target.value)}
              {...describedBy}
            />
          ))}
        </div>
      </Section>
      <div className="flex flex-col-reverse gap-3 border-t-2 border-ink pt-6 sm:flex-row sm:justify-end">
        <Link
          href="/employees"
          className={buttonVariants({
            variant: "secondary",
            className: "no-underline hover:text-ink",
          })}
        >
          Cancel
        </Link>
        <Button type="submit" disabled={pending}>
          {pending ? "Adding…" : "Add employee"}
        </Button>
      </div>
    </form>
  );
}
