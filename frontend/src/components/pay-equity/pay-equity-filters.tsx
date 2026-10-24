"use client";

import { useId } from "react";

import { usePayEquityState } from "@/components/insights/insights-state";
import {
  NativeSelect,
  NativeSelectOption,
} from "@/components/ui/native-select";
import type { components } from "@/lib/api/schema";

type ReferenceData = components["schemas"]["ReferenceData"];

/** The pay-equity country (bands are per country, in its currency) and department. */
export function PayEquityFilters({ reference }: { reference: ReferenceData }) {
  const [state, setState] = usePayEquityState();
  const countryId = useId();
  const departmentId = useId();
  const currencyOf = new Map(
    reference.countries.map((c) => [c.code, c.default_currency]),
  );

  return (
    <div className="flex w-full flex-wrap gap-3 sm:w-auto">
      <div className="flex min-w-0 flex-[1_1_160px] flex-col gap-1.5">
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
          <NativeSelectOption value="">Choose a country</NativeSelectOption>
          {reference.countries
            .filter((country) => country.is_active)
            .map((country) => (
              <NativeSelectOption key={country.code} value={country.code}>
                {country.name} ({currencyOf.get(country.code)})
              </NativeSelectOption>
            ))}
        </NativeSelect>
      </div>
      <div className="flex min-w-0 flex-[1_1_160px] flex-col gap-1.5">
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
