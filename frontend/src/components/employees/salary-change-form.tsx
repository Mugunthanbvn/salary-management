"use client";

import { useRouter } from "next/navigation";
import { useId, useState, useTransition } from "react";
import { toast } from "sonner";

import { recordSalaryChange } from "@/app/(app)/employees/actions";
import { MarginNote } from "@/components/print";
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
import { REASON_LABELS } from "@/lib/labels";
import { toMajorInput, toMinorUnits } from "@/lib/money-input";

import {
  ComponentsEditor,
  isComponentError,
  rowsFrom,
  toComponentsIn,
  type ComponentRow,
} from "./components-editor";
import {
  FieldError,
  FormDialog,
  FormProblem,
  invalidProps,
  unmatchedErrors,
} from "./form-dialog";
import { countryName, exponentOf, fullName, roleAndLevel } from "./format";

type EmployeeDetail = components["schemas"]["EmployeeDetail"];
type ReferenceData = components["schemas"]["ReferenceData"];
type SalaryReason = components["schemas"]["SalaryReason"];
type Level = components["schemas"]["Level"];
type SalaryChangeRequest = components["schemas"]["SalaryChangeRequest"];

const FIELDS = new Set([
  "effective_date",
  "reason",
  "job_role_id",
  "level",
  "country_code",
  "base_minor",
  "note",
]);

/**
 * Record a salary change (docs/13-frontend-ux.md §4.5): date, reason, an optional new role,
 * level or country, the new base pay and components, typed in major units and sent in
 * minor units. The API checks every rule (dates, promotions, currency) and its errors show
 * next to their fields; the form only checks that amounts are amounts.
 */
export function SalaryChangeDialog({
  open,
  onOpenChange,
  employee,
  reference,
  version,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  employee: EmployeeDetail;
  reference: ReferenceData;
  version: number;
}) {
  return open ? (
    <SalaryChangeForm
      onOpenChange={onOpenChange}
      employee={employee}
      reference={reference}
      version={version}
    />
  ) : null;
}

function SalaryChangeForm({
  onOpenChange,
  employee,
  reference,
  version,
}: {
  onOpenChange: (open: boolean) => void;
  employee: EmployeeDetail;
  reference: ReferenceData;
  version: number;
}) {
  const id = useId();
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const currentCurrency = employee.current_base?.currency ?? "";
  const currentExponent = exponentOf(currentCurrency, reference) ?? 0;

  const [today] = useState(todayIso);
  const [effectiveDate, setEffectiveDate] = useState(today);
  const [reason, setReason] = useState<SalaryReason>("MERIT");
  const [jobRoleId, setJobRoleId] = useState("");
  const [level, setLevel] = useState("");
  const [countryCode, setCountryCode] = useState("");
  const [base, setBase] = useState(() =>
    employee.current_base
      ? toMajorInput(employee.current_base.amount_minor, currentExponent)
      : "",
  );
  const [rows, setRows] = useState<ComponentRow[]>(() =>
    rowsFrom(employee.current_salary?.components ?? [], currentExponent),
  );
  const [note, setNote] = useState("");
  const [clientErrors, setClientErrors] = useState<Record<string, string>>({});
  const [problem, setProblem] = useState<PlainProblem | null>(null);

  // A move pays in the new country's currency (docs/07-api-spec.md §6.7).
  const newCountry = reference.countries.find((c) => c.code === countryCode);
  const currency = newCountry?.default_currency ?? currentCurrency;
  const exponent = exponentOf(currency, reference);
  const errors = { ...fieldErrors(problem), ...clientErrors };
  const error = (key: string) => errors[key];
  const unmatched = unmatchedErrors(
    errors,
    (key) => FIELDS.has(key) || isComponentError(key),
  );

  function submit() {
    if (exponent === null) {
      setClientErrors({
        base_minor: `${currency} amounts can't be entered here.`,
      });
      return;
    }
    const next: Record<string, string> = {};
    if (!effectiveDate)
      next.effective_date = "Enter the date the change takes effect";
    const baseMinor = toMinorUnits(base, currency, exponent);
    if (!baseMinor.ok) next.base_minor = baseMinor.message;
    const list = toComponentsIn(rows, currency, exponent);
    Object.assign(next, list.errors);
    setClientErrors(next);
    setProblem(null);
    if (Object.keys(next).length || !baseMinor.ok) return;

    const body: SalaryChangeRequest = {
      version,
      effective_date: effectiveDate,
      reason,
      ...(jobRoleId ? { job_role_id: Number(jobRoleId) } : {}),
      ...(level ? { level: level as Level } : {}),
      ...(countryCode ? { country_code: countryCode } : {}),
      base_minor: baseMinor.minor,
      components: list.components,
      ...(note.trim() ? { note: note.trim() } : {}),
    };
    startTransition(async () => {
      const result = await recordSalaryChange(employee.id, body);
      if (result.ok) {
        toast.success("Salary change recorded.");
        onOpenChange(false);
      } else {
        setProblem(result.problem);
      }
    });
  }

  const currentLevel = reference.levels.find((l) => l.code === employee.level);
  const reasons = reference.salary_change_reasons.filter((r) => r !== "HIRE");

  return (
    <FormDialog
      open
      onOpenChange={onOpenChange}
      title="Record a salary change"
      description={`${fullName(employee)}, ${roleAndLevel(employee)}, ${countryName(employee.country_code, reference)}.`}
      submitLabel="Record salary change"
      pendingLabel="Recording…"
      pending={pending}
      onSubmit={submit}
      wide
    >
      <FormProblem
        problem={problem}
        unmatched={unmatched}
        onReload={() => {
          router.refresh();
          onOpenChange(false);
        }}
      />

      <div className="grid gap-5 sm:grid-cols-2">
        <div className="flex flex-col gap-2">
          <Label htmlFor={`${id}-date`}>Effective date</Label>
          <Input
            id={`${id}-date`}
            type="date"
            max={today}
            value={effectiveDate}
            onChange={(event) => setEffectiveDate(event.target.value)}
            {...invalidProps(`${id}-date-error`, error("effective_date"))}
          />
          <FieldError
            id={`${id}-date-error`}
            message={error("effective_date")}
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor={`${id}-reason`}>Reason</Label>
          <NativeSelect
            id={`${id}-reason`}
            value={reason}
            onChange={(event) => setReason(event.target.value as SalaryReason)}
            {...invalidProps(`${id}-reason-error`, error("reason"))}
          >
            {reasons.map((value) => (
              <NativeSelectOption key={value} value={value}>
                {REASON_LABELS[value]}
              </NativeSelectOption>
            ))}
          </NativeSelect>
          <FieldError id={`${id}-reason-error`} message={error("reason")} />
        </div>
      </div>

      <ChangeSelect
        id={`${id}-role`}
        label="New job role"
        current={employee.job_role.title}
        value={jobRoleId}
        onChange={setJobRoleId}
        error={error("job_role_id")}
        options={reference.job_roles.map((r) => ({
          value: String(r.id),
          label: r.title,
        }))}
      />
      <div className="grid gap-5 sm:grid-cols-2">
        <ChangeSelect
          id={`${id}-level`}
          label="New level"
          current={
            currentLevel
              ? `${currentLevel.code} ${currentLevel.label}`
              : employee.level
          }
          value={level}
          onChange={setLevel}
          error={error("level")}
          options={reference.levels.map((l) => ({
            value: l.code,
            label: `${l.code} ${l.label}`,
          }))}
        />
        <ChangeSelect
          id={`${id}-country`}
          label="New country"
          current={countryName(employee.country_code, reference)}
          value={countryCode}
          onChange={setCountryCode}
          error={error("country_code")}
          options={reference.countries
            .filter((c) => c.is_active && c.code !== employee.country_code)
            .map((c) => ({ value: c.code, label: c.name }))}
        />
      </div>
      {newCountry && newCountry.default_currency !== currentCurrency ? (
        <MarginNote>
          Moving to {newCountry.name}: pay will be in{" "}
          {newCountry.default_currency}. Enter every amount in{" "}
          {newCountry.default_currency}.
        </MarginNote>
      ) : null}

      <div className="flex flex-col gap-2 sm:max-w-xs">
        <Label htmlFor={`${id}-base`}>New base pay ({currency} a year)</Label>
        <Input
          id={`${id}-base`}
          inputMode="decimal"
          autoComplete="off"
          value={base}
          onChange={(event) => setBase(event.target.value)}
          className="font-serif text-[19px]"
          {...invalidProps(`${id}-base-error`, error("base_minor"))}
        />
        <FieldError id={`${id}-base-error`} message={error("base_minor")} />
      </div>

      <ComponentsEditor
        rows={rows}
        onChange={setRows}
        currency={currency}
        errors={errors}
        replaces
      />

      <div className="flex flex-col gap-2">
        <Label htmlFor={`${id}-note`}>Note</Label>
        <Textarea
          id={`${id}-note`}
          value={note}
          maxLength={500}
          onChange={(event) => setNote(event.target.value)}
          {...invalidProps(`${id}-note-error`, error("note"))}
        />
        <FieldError id={`${id}-note-error`} message={error("note")} />
      </div>
    </FormDialog>
  );
}

function ChangeSelect({
  id,
  label,
  current,
  value,
  onChange,
  error,
  options,
}: {
  id: string;
  label: string;
  current: string;
  value: string;
  onChange: (value: string) => void;
  error?: string;
  options: { value: string; label: string }[];
}) {
  return (
    <div className="flex min-w-0 flex-col gap-2">
      <Label htmlFor={id}>{label}</Label>
      <NativeSelect
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        {...invalidProps(`${id}-error`, error)}
      >
        <NativeSelectOption value="">No change ({current})</NativeSelectOption>
        {options.map((option) => (
          <NativeSelectOption key={option.value} value={option.value}>
            {option.label}
          </NativeSelectOption>
        ))}
      </NativeSelect>
      <FieldError id={`${id}-error`} message={error} />
    </div>
  );
}
