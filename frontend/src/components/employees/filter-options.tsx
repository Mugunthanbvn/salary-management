"use client";

import { useId } from "react";

import { Checkbox } from "@/components/ui/checkbox";

import type { FilterDef } from "./filters";

/**
 * One filter's choices as checkboxes under its name (a fieldset): in a popover on a
 * desktop, in the Filters sheet on a phone. Each row is a 44 px tap target.
 */
export function FilterOptions({
  def,
  values,
  onChange,
}: {
  def: FilterDef;
  values: string[];
  onChange: (values: string[]) => void;
}) {
  const id = useId();
  return (
    <fieldset className="min-w-0">
      <legend className="mb-1 text-sm font-bold text-ink-2">{def.label}</legend>
      <ul>
        {def.options.map((option) => {
          const optionId = `${id}-${option.value}`;
          const checked = values.includes(option.value);
          return (
            <li key={option.value}>
              <label
                htmlFor={optionId}
                className="flex min-h-11 cursor-pointer items-center gap-3 text-[15px]"
              >
                <Checkbox
                  id={optionId}
                  checked={checked}
                  onCheckedChange={(next) =>
                    onChange(
                      next === true
                        ? [...values, option.value]
                        : values.filter((value) => value !== option.value),
                    )
                  }
                />
                {option.label}
              </label>
            </li>
          );
        })}
      </ul>
    </fieldset>
  );
}
