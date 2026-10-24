"use client";

import { useRouter } from "next/navigation";
import { useId, useState, useTransition } from "react";
import { toast } from "sonner";

import {
  reactivateEmployee,
  terminateEmployee,
  updateEmployee,
} from "@/app/(app)/employees/actions";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  NativeSelect,
  NativeSelectOption,
} from "@/components/ui/native-select";
import { Textarea } from "@/components/ui/textarea";
import {
  fieldErrors,
  type ActionResult,
  type PlainProblem,
} from "@/lib/api/action-result";
import type { components } from "@/lib/api/schema";
import { formatDate, todayIso } from "@/lib/dates";
import { EMPLOYMENT_TYPE_LABELS, EMPLOYMENT_TYPES } from "@/lib/labels";

import {
  FieldError,
  FormDialog,
  FormProblem,
  invalidProps,
  unmatchedErrors,
} from "./form-dialog";
import { fullName } from "./format";

type EmployeeDetail = components["schemas"]["EmployeeDetail"];
type EmployeeUpdate = components["schemas"]["EmployeeUpdate"];
type EmploymentType = components["schemas"]["EmploymentType"];

type DialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  employee: EmployeeDetail;
  version: number;
};

/** Sends a change; on success says so and closes, otherwise keeps the problem to show. */
function useSubmit(onOpenChange: (open: boolean) => void) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [problem, setProblem] = useState<PlainProblem | null>(null);
  function submit<T>(send: () => Promise<ActionResult<T>>, success: string) {
    setProblem(null);
    startTransition(async () => {
      const result = await send();
      if (result.ok) {
        toast.success(success);
        onOpenChange(false);
      } else {
        setProblem(result.problem);
      }
    });
  }
  function reload() {
    router.refresh();
    onOpenChange(false);
  }
  return { pending, problem, submit, reload };
}

/** Profile fields only (docs/07-api-spec.md §6.4): role, level, country and pay change through a salary change. */
export function EditDetailsDialog(props: DialogProps) {
  return props.open ? <EditDetailsForm {...props} /> : null;
}

function EditDetailsForm({ onOpenChange, employee, version }: DialogProps) {
  const id = useId();
  const { pending, problem, submit, reload } = useSubmit(onOpenChange);
  const [firstName, setFirstName] = useState(employee.first_name);
  const [lastName, setLastName] = useState(employee.last_name);
  const [email, setEmail] = useState(employee.email);
  const [type, setType] = useState<EmploymentType>(employee.employment_type);
  const errors = fieldErrors(problem);
  const shown = new Set([
    "first_name",
    "last_name",
    "email",
    "employment_type",
  ]);

  function save() {
    const changes: Omit<EmployeeUpdate, "version"> = {};
    if (firstName.trim() !== employee.first_name)
      changes.first_name = firstName.trim();
    if (lastName.trim() !== employee.last_name)
      changes.last_name = lastName.trim();
    if (email.trim() !== employee.email) changes.email = email.trim();
    if (type !== employee.employment_type) changes.employment_type = type;
    if (Object.keys(changes).length === 0) {
      onOpenChange(false);
      return;
    }
    submit(
      () => updateEmployee(employee.id, { version, ...changes }),
      "Details saved.",
    );
  }

  const text = (
    key: "first_name" | "last_name" | "email",
    label: string,
    value: string,
    setValue: (value: string) => void,
    inputType = "text",
  ) => (
    <div className="flex flex-col gap-2">
      <Label htmlFor={`${id}-${key}`}>{label}</Label>
      <Input
        id={`${id}-${key}`}
        type={inputType}
        value={value}
        autoComplete="off"
        onChange={(event) => setValue(event.target.value)}
        {...invalidProps(`${id}-${key}-error`, errors[key])}
      />
      <FieldError id={`${id}-${key}-error`} message={errors[key]} />
    </div>
  );

  return (
    <FormDialog
      open
      onOpenChange={onOpenChange}
      title={`Edit ${fullName(employee)}'s details`}
      description="Job role, level, country and pay change through a salary change, so their history explains them."
      submitLabel="Save details"
      pendingLabel="Saving…"
      pending={pending}
      onSubmit={save}
    >
      <FormProblem
        problem={problem}
        unmatched={unmatchedErrors(errors, (key) => shown.has(key))}
        onReload={reload}
      />
      <div className="grid gap-5 sm:grid-cols-2">
        {text("first_name", "First name", firstName, setFirstName)}
        {text("last_name", "Last name", lastName, setLastName)}
      </div>
      {text("email", "Email", email, setEmail, "email")}
      <div className="flex flex-col gap-2">
        <Label htmlFor={`${id}-type`}>Employment type</Label>
        <NativeSelect
          id={`${id}-type`}
          value={type}
          onChange={(event) => setType(event.target.value as EmploymentType)}
          {...invalidProps(`${id}-type-error`, errors.employment_type)}
        >
          {EMPLOYMENT_TYPES.map((value) => (
            <NativeSelectOption key={value} value={value}>
              {EMPLOYMENT_TYPE_LABELS[value]}
            </NativeSelectOption>
          ))}
        </NativeSelect>
        <FieldError id={`${id}-type-error`} message={errors.employment_type} />
      </div>
    </FormDialog>
  );
}

/** Terminate (docs/07-api-spec.md §6.5): the last day, never before the hire date, and a note. */
export function TerminateDialog(props: DialogProps) {
  return props.open ? <TerminateForm {...props} /> : null;
}

function TerminateForm({ onOpenChange, employee, version }: DialogProps) {
  const id = useId();
  const { pending, problem, submit, reload } = useSubmit(onOpenChange);
  const [date, setDate] = useState(todayIso);
  const [note, setNote] = useState("");
  const [dateError, setDateError] = useState<string | undefined>();
  const errors = fieldErrors(problem);
  const shownDateError = dateError ?? errors.termination_date;
  const name = fullName(employee);

  function terminate() {
    // The same check and words as the API's `before_hire_date`, to save a round trip.
    if (date && date < employee.hire_date) {
      setDateError(
        `The employee was hired on ${formatDate(employee.hire_date)}.`,
      );
      return;
    }
    setDateError(undefined);
    submit(
      () =>
        terminateEmployee(employee.id, {
          version,
          ...(date ? { termination_date: date } : {}),
          ...(note.trim() ? { note: note.trim() } : {}),
        }),
      `${name} was terminated.`,
    );
  }

  return (
    <FormDialog
      open
      onOpenChange={onOpenChange}
      title={`Terminate ${name}?`}
      description={`They leave the list of active employees. Their pay history stays, and they can be reactivated. Hired ${formatDate(employee.hire_date)}.`}
      submitLabel="Terminate"
      pendingLabel="Terminating…"
      pending={pending}
      onSubmit={terminate}
      destructive
    >
      <FormProblem
        problem={problem}
        unmatched={unmatchedErrors(
          errors,
          (key) => key === "termination_date" || key === "note",
        )}
        onReload={reload}
      />
      <div className="flex flex-col gap-2 sm:max-w-xs">
        <Label htmlFor={`${id}-date`}>Last day</Label>
        <Input
          id={`${id}-date`}
          type="date"
          min={employee.hire_date}
          value={date}
          onChange={(event) => setDate(event.target.value)}
          {...invalidProps(`${id}-date-error`, shownDateError)}
        />
        <FieldError id={`${id}-date-error`} message={shownDateError} />
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor={`${id}-note`}>Note</Label>
        <Textarea
          id={`${id}-note`}
          value={note}
          maxLength={500}
          onChange={(event) => setNote(event.target.value)}
          {...invalidProps(`${id}-note-error`, errors.note)}
        />
        <FieldError id={`${id}-note-error`} message={errors.note} />
      </div>
    </FormDialog>
  );
}

/** Reactivate (docs/07-api-spec.md §6.5): back to active, the termination date cleared. */
export function ReactivateDialog(props: DialogProps) {
  return props.open ? <ReactivateForm {...props} /> : null;
}

function ReactivateForm({ onOpenChange, employee, version }: DialogProps) {
  const { pending, problem, submit, reload } = useSubmit(onOpenChange);
  const name = fullName(employee);
  return (
    <FormDialog
      open
      onOpenChange={onOpenChange}
      title={`Reactivate ${name}?`}
      description="They become an active employee again, with the pay they had."
      submitLabel="Reactivate"
      pendingLabel="Reactivating…"
      pending={pending}
      onSubmit={() =>
        submit(
          () => reactivateEmployee(employee.id, { version }),
          `${name} was reactivated.`,
        )
      }
    >
      <FormProblem
        problem={problem}
        unmatched={Object.values(fieldErrors(problem))}
        onReload={reload}
      />
    </FormDialog>
  );
}
