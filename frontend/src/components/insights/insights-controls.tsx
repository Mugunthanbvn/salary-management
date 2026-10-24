"use client";

import { ChevronDownIcon } from "lucide-react";
import { useId, type ReactNode } from "react";

import { Checkbox } from "@/components/ui/checkbox";
import {
  NativeSelect,
  NativeSelectOption,
} from "@/components/ui/native-select";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { SegmentedControl } from "@/components/ui/segmented-control";
import type { components } from "@/lib/api/schema";
import { populationLabel } from "@/lib/insights-params";
import {
  EMPLOYEE_STATUSES,
  EMPLOYMENT_TYPES,
  EMPLOYMENT_TYPE_LABELS,
  STATUS_LABELS,
} from "@/lib/labels";

import { useInsightsPending, useInsightsState } from "./insights-state";

type ReferenceData = components["schemas"]["ReferenceData"];

/** The Base / Total and Yearly / Monthly toggles (docs/13-frontend-ux.md §3.4). */
export function PayToggles() {
  const [state, setState] = useInsightsState();
  return (
    <div className="flex w-full flex-wrap gap-3 sm:w-auto">
      <SegmentedControl
        label="Pay basis"
        options={[
          { value: "base", label: "Base pay" },
          { value: "total", label: "Total pay" },
        ]}
        value={state.comp}
        onChange={(comp) => void setState({ comp })}
        className="flex-1 sm:flex-none [&>button]:flex-1"
      />
      <SegmentedControl
        label="Period"
        options={[
          { value: "annual", label: "Yearly" },
          { value: "monthly", label: "Monthly" },
        ]}
        value={state.period}
        // Display only: the API's amounts are annual, so nothing is fetched again.
        onChange={(period) => void setState({ period }, { shallow: true })}
        className="flex-1 sm:flex-none [&>button]:flex-1"
      />
    </div>
  );
}

/**
 * Who the figures are about, and what narrows them: the population chip ("Full-time ·
 * Active", the API's default made visible) and the country and department filters.
 */
export function InsightsControls({ reference }: { reference: ReferenceData }) {
  const [state, setState] = useInsightsState();
  const countryId = useId();
  const departmentId = useId();
  const countries = reference.countries.filter((country) => country.is_active);

  return (
    <div className="mt-6 flex flex-wrap items-end gap-x-4 gap-y-3">
      <PopulationChip />
      <div className="flex min-w-0 flex-[1_1_180px] flex-col gap-1.5 sm:flex-none">
        <label htmlFor={countryId} className="text-sm text-ink-2">
          Country
        </label>
        <NativeSelect
          id={countryId}
          value={state.country ?? ""}
          onChange={(event) =>
            void setState({ country: event.target.value || null })
          }
          className="sm:w-56"
        >
          <NativeSelectOption value="">All countries</NativeSelectOption>
          {countries.map((country) => (
            <NativeSelectOption key={country.code} value={country.code}>
              {country.name}
            </NativeSelectOption>
          ))}
        </NativeSelect>
      </div>
      <div className="flex min-w-0 flex-[1_1_180px] flex-col gap-1.5 sm:flex-none">
        <label htmlFor={departmentId} className="text-sm text-ink-2">
          Department
        </label>
        <NativeSelect
          id={departmentId}
          value={state.department_id?.toString() ?? ""}
          onChange={(event) =>
            void setState({
              department_id: event.target.value
                ? Number(event.target.value)
                : null,
            })
          }
          className="sm:w-56"
        >
          <NativeSelectOption value="">All departments</NativeSelectOption>
          {reference.departments.map((department) => (
            <NativeSelectOption key={department.id} value={department.id}>
              {department.name}
            </NativeSelectOption>
          ))}
        </NativeSelect>
      </div>
    </div>
  );
}

function PopulationChip() {
  const [state, setState] = useInsightsState();
  const label = populationLabel(state.employment_type, state.status);

  function toggle<T extends string>(list: T[], value: T, on: boolean): T[] {
    return on ? [...list, value] : list.filter((item) => item !== value);
  }

  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-sm text-ink-2">People</span>
      <Popover>
        <PopoverTrigger className="inline-flex min-h-11 max-w-full cursor-pointer items-center gap-2 rounded-control border border-ink bg-paper px-3 py-1.5 text-left text-base">
          <span className="sr-only">Change who is counted: </span>
          {label}
          <ChevronDownIcon
            className="size-5 shrink-0 text-ink-2"
            aria-hidden="true"
          />
        </PopoverTrigger>
        <PopoverContent className="w-72">
          <CheckGroup
            legend="Employment type"
            values={EMPLOYMENT_TYPES}
            labels={EMPLOYMENT_TYPE_LABELS}
            selected={state.employment_type}
            onChange={(value, on) =>
              void setState({
                employment_type: toggle(state.employment_type, value, on),
              })
            }
          />
          <CheckGroup
            legend="Status"
            values={EMPLOYEE_STATUSES}
            labels={STATUS_LABELS}
            selected={state.status}
            onChange={(value, on) =>
              void setState({ status: toggle(state.status, value, on) })
            }
          />
          <p className="text-sm text-ink-2">
            Part-time pay isn&apos;t full-time equivalent, so it pulls medians
            down.
          </p>
        </PopoverContent>
      </Popover>
    </div>
  );
}

function CheckGroup<T extends string>({
  legend,
  values,
  labels,
  selected,
  onChange,
}: {
  legend: string;
  values: readonly T[];
  labels: Record<T, string>;
  selected: T[];
  onChange: (value: T, on: boolean) => void;
}) {
  const id = useId();
  return (
    <fieldset>
      <legend className="mb-1 text-sm font-bold">{legend}</legend>
      {values.map((value) => {
        const checked = selected.includes(value);
        // At least one stays ticked: an empty list would mean "nobody".
        const last = checked && selected.length === 1;
        return (
          <div key={value} className="flex min-h-11 items-center gap-3">
            <Checkbox
              id={`${id}-${value}`}
              checked={checked}
              disabled={last}
              onCheckedChange={(on) => onChange(value, on === true)}
            />
            <label htmlFor={`${id}-${value}`} className="cursor-pointer">
              {labels[value]}
            </label>
          </div>
        );
      })}
    </fieldset>
  );
}

/** Job pay by role alone, or split by level too (`split_by_level`). */
export function SplitByLevelToggle() {
  const [state, setState] = useInsightsState();
  return (
    <SegmentedControl
      label="Group jobs by"
      options={[
        { value: "role", label: "Job" },
        { value: "level", label: "Job and level" },
      ]}
      value={state.split_by_level ? "level" : "role"}
      onChange={(value) => void setState({ split_by_level: value === "level" })}
    />
  );
}

/** Top or bottom earners (`direction`). */
export function DirectionToggle() {
  const [state, setState] = useInsightsState();
  return (
    <SegmentedControl
      label="Earners"
      options={[
        { value: "top", label: "Highest paid" },
        { value: "bottom", label: "Lowest paid" },
      ]}
      value={state.direction}
      onChange={(direction) => void setState({ direction })}
    />
  );
}

/** Dims the figures while the server renders new ones for a changed filter. */
export function InsightsBusy({ children }: { children: ReactNode }) {
  const pending = useInsightsPending();
  return (
    <div
      aria-busy={pending || undefined}
      className={
        pending ? "opacity-60 transition-opacity" : "transition-opacity"
      }
    >
      {children}
    </div>
  );
}
