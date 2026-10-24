"use client";

import { PlusIcon, Trash2Icon } from "lucide-react";
import { useId } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  NativeSelect,
  NativeSelectOption,
} from "@/components/ui/native-select";
import type { components } from "@/lib/api/schema";
import { COMPONENT_TYPE_LABELS, COMPONENT_TYPES } from "@/lib/labels";
import { toMajorInput, toMinorUnits } from "@/lib/money-input";

import { FieldError, invalidProps } from "./form-dialog";

type Component = components["schemas"]["Component"];
type ComponentIn = components["schemas"]["ComponentIn"];
type ComponentType = components["schemas"]["ComponentType"];

/** One component as the person edits it: the amount is text in major units. */
export type ComponentRow = {
  key: number;
  type: ComponentType;
  name: string;
  amount: string;
};

let nextKey = 0;

export function newRow(): ComponentRow {
  nextKey += 1;
  return { key: nextKey, type: "ALLOWANCE", name: "", amount: "" };
}

/** The current record's components, as rows to edit (components are not inherited). */
export function rowsFrom(list: Component[], exponent: number): ComponentRow[] {
  return list.map((component) => ({
    ...newRow(),
    type: component.type,
    name: component.name,
    amount: toMajorInput(component.amount.amount_minor, exponent),
  }));
}

/**
 * The rows as the API takes them (minor units), or the errors keyed like the API's
 * (`components.1.amount_minor`), so client and API errors show in the same place.
 */
export function toComponentsIn(
  rows: ComponentRow[],
  currency: string,
  exponent: number,
  prefix = "components",
): { components: ComponentIn[]; errors: Record<string, string> } {
  const errors: Record<string, string> = {};
  const list: ComponentIn[] = [];
  rows.forEach((row, index) => {
    const name = row.name.trim();
    if (!name) errors[`${prefix}.${index}.name`] = "Enter a name";
    const amount = toMinorUnits(row.amount, currency, exponent);
    if (!amount.ok) errors[`${prefix}.${index}.amount_minor`] = amount.message;
    else list.push({ type: row.type, name, amount_minor: amount.minor });
  });
  return { components: list, errors };
}

/** True for an error key this editor shows next to a field. */
export function isComponentError(key: string, prefix = "components"): boolean {
  return (
    key === prefix ||
    new RegExp(
      `^${prefix.replaceAll(".", "\\.")}\\.\\d+\\.(type|name|amount_minor)$`,
    ).test(key)
  );
}

/**
 * Allowances and bonus targets on top of base pay: add, change or remove rows. In a salary
 * change the list replaces the current set (`replaces`), so it starts as a copy of it.
 */
export function ComponentsEditor({
  rows,
  onChange,
  currency,
  errors,
  prefix = "components",
  replaces = false,
}: {
  rows: ComponentRow[];
  onChange: (rows: ComponentRow[]) => void;
  currency: string;
  errors: Record<string, string>;
  prefix?: string;
  replaces?: boolean;
}) {
  const id = useId();
  const update = (key: number, patch: Partial<ComponentRow>) =>
    onChange(rows.map((row) => (row.key === key ? { ...row, ...patch } : row)));
  const listError = errors[prefix];
  return (
    <div className="flex flex-col gap-3">
      <div>
        <p className="text-sm font-bold text-ink-2">
          Allowances and bonus targets
        </p>
        <p className="text-sm text-ink-2">
          Yearly amounts in {currency}.
          {replaces ? " The list replaces the current one." : ""}
        </p>
      </div>
      <FieldError id={`${id}-list-error`} message={listError} />
      {rows.map((row, index) => {
        const base = `${id}-${row.key}`;
        const error = (field: string) => errors[`${prefix}.${index}.${field}`];
        return (
          <fieldset
            key={row.key}
            className="grid grid-cols-[minmax(0,1fr)_auto] gap-x-3 gap-y-2 border-t border-rule pt-3 sm:grid-cols-[150px_minmax(0,1fr)_150px_auto] sm:items-start"
          >
            <legend className="sr-only">Component {index + 1}</legend>
            <div className="col-span-2 flex flex-col gap-1.5 sm:col-span-1">
              <Label htmlFor={`${base}-type`}>Type</Label>
              <NativeSelect
                id={`${base}-type`}
                value={row.type}
                onChange={(event) =>
                  update(row.key, { type: event.target.value as ComponentType })
                }
                {...invalidProps(`${base}-type-error`, error("type"))}
              >
                {COMPONENT_TYPES.map((type) => (
                  <NativeSelectOption key={type} value={type}>
                    {COMPONENT_TYPE_LABELS[type]}
                  </NativeSelectOption>
                ))}
              </NativeSelect>
              <FieldError id={`${base}-type-error`} message={error("type")} />
            </div>
            <div className="col-span-2 flex flex-col gap-1.5 sm:col-span-1">
              <Label htmlFor={`${base}-name`}>Name</Label>
              <Input
                id={`${base}-name`}
                value={row.name}
                maxLength={60}
                onChange={(event) =>
                  update(row.key, { name: event.target.value })
                }
                {...invalidProps(`${base}-name-error`, error("name"))}
              />
              <FieldError id={`${base}-name-error`} message={error("name")} />
            </div>
            <div className="flex min-w-0 flex-col gap-1.5">
              <Label htmlFor={`${base}-amount`}>
                Amount ({currency} a year)
              </Label>
              <Input
                id={`${base}-amount`}
                inputMode="decimal"
                autoComplete="off"
                value={row.amount}
                onChange={(event) =>
                  update(row.key, { amount: event.target.value })
                }
                {...invalidProps(`${base}-amount-error`, error("amount_minor"))}
              />
              <FieldError
                id={`${base}-amount-error`}
                message={error("amount_minor")}
              />
            </div>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="mt-[26px]"
              aria-label={`Remove ${row.name.trim() || `component ${index + 1}`}`}
              onClick={() =>
                onChange(rows.filter((other) => other.key !== row.key))
              }
            >
              <Trash2Icon aria-hidden="true" />
            </Button>
          </fieldset>
        );
      })}
      <div>
        <Button
          type="button"
          variant="secondary"
          onClick={() => onChange([...rows, newRow()])}
        >
          <PlusIcon aria-hidden="true" />
          Add a component
        </Button>
      </div>
    </div>
  );
}
