"use client";

import { cn } from "cn";
import { XIcon } from "lucide-react";
import { debounce } from "nuqs";
import { useId } from "react";

import { useMe } from "@/components/shell/me-context";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { SegmentedControl } from "@/components/ui/segmented-control";
import {
  Sheet,
  SheetClose,
  SheetContent,
  SheetFooter,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import type { components } from "@/lib/api/schema";
import {
  CLEARED_FILTERS,
  hasFilters,
  type DirectoryState,
} from "@/lib/directory-params";
import { formatCount } from "@/lib/numbers";

import { useDirectoryState } from "./directory-state";
import { FilterOptions } from "./filter-options";
import {
  filterDefs,
  filterPatch,
  isActive,
  selectedValues,
  summary,
  type DirectoryPatch,
  type FilterDef,
} from "./filters";
import {
  PAY_NEEDS_ONE_CURRENCY,
  PayRange,
  payCurrency,
  paySummary,
} from "./pay-range";
import { SortSelect } from "./sort-select";

type ReferenceData = components["schemas"]["ReferenceData"];

const SEARCH_DEBOUNCE_MS = 300;

/**
 * Everything that narrows or orders the directory: the search, the filters (inline on a
 * desktop; a "Filters (n)" bottom sheet with removable chips on a phone), the sort and, with
 * SALARY_READ, the pay range and the Base/Total and Annual/Monthly toggles. Every control
 * writes the URL, which the server reads to call GET /employees.
 */
export function DirectoryToolbar({
  reference,
  total,
}: {
  reference: ReferenceData;
  total: number;
}) {
  const me = useMe();
  const [state, setState] = useDirectoryState();
  const showPay = me.can("SALARY_READ");
  const defs = filterDefs(reference);
  const payComparable = payCurrency(state, reference) !== null;
  const update = (patch: DirectoryPatch) => void setState(patch);
  const clear = () => update(CLEARED_FILTERS);

  return (
    <div className="mt-8 sm:mt-10">
      <SearchBox
        value={state.q}
        onChange={(q) =>
          void setState(
            { q: q || null, page: null },
            {
              history: "replace",
              limitUrlUpdates: debounce(SEARCH_DEBOUNCE_MS),
            },
          )
        }
      />

      <PhoneFilters
        defs={defs}
        state={state}
        reference={reference}
        total={total}
        showPay={showPay}
        payComparable={payComparable}
        onChange={update}
        onClear={clear}
      />

      <div
        role="group"
        aria-label="Filters"
        className="mt-5 hidden flex-wrap items-center gap-2.5 sm:flex"
      >
        {defs.map((def) => (
          <FilterPopover
            key={def.key}
            def={def}
            values={selectedValues(state, def.key)}
            active={isActive(state, def.key)}
            onChange={(values) => update(filterPatch(def.key, values))}
          />
        ))}
        {showPay ? (
          <PayPopover state={state} reference={reference} onChange={update} />
        ) : null}
        {hasFilters(state) ? (
          <Button variant="link" className="ml-1 text-sm" onClick={clear}>
            Clear filters
          </Button>
        ) : null}
      </div>

      <div className="mt-4 flex flex-wrap items-end justify-between gap-3 sm:mt-6">
        <div className="hidden sm:block">
          <SortSelect
            value={state.sort}
            onChange={(sort) => update({ sort, page: null })}
            showPay={showPay}
            payComparable={payComparable}
            hint={PAY_NEEDS_ONE_CURRENCY}
          />
        </div>
        {showPay ? (
          <div className="flex flex-wrap gap-3">
            <SegmentedControl
              label="Pay shown"
              options={[
                { value: "base", label: "Base" },
                { value: "total", label: "Total" },
              ]}
              value={state.comp}
              onChange={(comp) => update({ comp })}
            />
            <SegmentedControl
              label="Period"
              options={[
                { value: "annual", label: "A year" },
                { value: "monthly", label: "A month" },
              ]}
              value={state.period}
              // Display only: the server doesn't need to know.
              onChange={(period) =>
                void setState({ period }, { shallow: true })
              }
            />
          </div>
        ) : null}
      </div>
    </div>
  );
}

function SearchBox({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  const id = useId();
  const tooShort = value.trim().length === 1;
  return (
    <form role="search" onSubmit={(event) => event.preventDefault()}>
      <label htmlFor={id} className="mb-1 block text-sm text-ink-2 sm:mb-2">
        Search by name, employee code or email
      </label>
      <input
        id={id}
        type="search"
        autoComplete="off"
        spellCheck={false}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        aria-describedby={tooShort ? `${id}-hint` : undefined}
        className="w-full rounded-none border-0 border-b-2 border-ink bg-transparent py-2 font-serif text-[22px] leading-tight text-ink outline-offset-4 placeholder:text-ink-3 sm:py-2.5 sm:text-[26px]"
      />
      {tooShort ? (
        <p id={`${id}-hint`} className="mt-2 text-sm text-ink-2">
          Type at least 2 characters to search.
        </p>
      ) : null}
    </form>
  );
}

const FILTER_BUTTON =
  "inline-flex min-h-11 cursor-pointer items-center rounded-control border border-ink bg-paper px-3.5 text-sm text-ink hover:bg-rule";

function FilterPopover({
  def,
  values,
  active,
  onChange,
}: {
  def: FilterDef;
  values: string[];
  active: boolean;
  onChange: (values: string[]) => void;
}) {
  return (
    <Popover>
      <PopoverTrigger className={cn(FILTER_BUTTON, active && "font-bold")}>
        {def.label}: {summary(def, values)}
      </PopoverTrigger>
      <PopoverContent aria-label={def.label}>
        <FilterOptions def={def} values={values} onChange={onChange} />
      </PopoverContent>
    </Popover>
  );
}

function PayPopover({
  state,
  reference,
  onChange,
}: {
  state: DirectoryState;
  reference: ReferenceData;
  onChange: (patch: DirectoryPatch) => void;
}) {
  const range = paySummary(state, reference);
  return (
    <Popover>
      <PopoverTrigger className={cn(FILTER_BUTTON, range && "font-bold")}>
        Pay: {range ?? "any"}
      </PopoverTrigger>
      <PopoverContent aria-label="Pay" className="w-96">
        <PayRange state={state} reference={reference} onChange={onChange} />
      </PopoverContent>
    </Popover>
  );
}

type Chip = { key: string; label: string; remove: DirectoryPatch };

/** The active filters as chips under the search box on a phone. */
function chipsFor(
  defs: FilterDef[],
  state: DirectoryState,
  reference: ReferenceData,
): Chip[] {
  const chips: Chip[] = [];
  for (const def of defs) {
    if (!isActive(state, def.key)) continue;
    const values = selectedValues(state, def.key);
    for (const value of values) {
      const label = def.options.find((o) => o.value === value)?.label ?? value;
      chips.push({
        key: `${def.key}-${value}`,
        label,
        remove: filterPatch(
          def.key,
          values.filter((v) => v !== value),
        ),
      });
    }
  }
  const range = paySummary(state, reference);
  if (range) {
    chips.push({
      key: "pay",
      label: `Pay ${range}`,
      remove: { salary_min: null, salary_max: null, page: null },
    });
  }
  return chips;
}

function PhoneFilters({
  defs,
  state,
  reference,
  total,
  showPay,
  payComparable,
  onChange,
  onClear,
}: {
  defs: FilterDef[];
  state: DirectoryState;
  reference: ReferenceData;
  total: number;
  showPay: boolean;
  payComparable: boolean;
  onChange: (patch: DirectoryPatch) => void;
  onClear: () => void;
}) {
  const chips = chipsFor(defs, state, reference);
  return (
    <div data-slot="phone-filters" className="mt-4 sm:hidden">
      <div className="flex items-center gap-3">
        <Sheet>
          <SheetTrigger asChild>
            <Button variant="secondary" className="font-normal">
              Filters ({chips.length})
            </Button>
          </SheetTrigger>
          <SheetContent side="bottom" className="max-h-[85dvh]">
            <SheetHeader>
              <SheetTitle>Filters</SheetTitle>
            </SheetHeader>
            <div className="flex flex-col gap-6 px-4 py-4">
              <SortSelect
                value={state.sort}
                onChange={(sort) => onChange({ sort, page: null })}
                showPay={showPay}
                payComparable={payComparable}
                hint={PAY_NEEDS_ONE_CURRENCY}
              />
              {showPay ? (
                <section aria-label="Pay">
                  <h3 className="mb-2 text-sm font-bold text-ink-2">Pay</h3>
                  <PayRange
                    state={state}
                    reference={reference}
                    onChange={onChange}
                  />
                </section>
              ) : null}
              {defs.map((def) => (
                <FilterOptions
                  key={def.key}
                  def={def}
                  values={selectedValues(state, def.key)}
                  onChange={(values) => onChange(filterPatch(def.key, values))}
                />
              ))}
            </div>
            <SheetFooter className="flex-row">
              <SheetClose asChild>
                <Button className="flex-1">Show results</Button>
              </SheetClose>
              <Button variant="secondary" onClick={onClear}>
                Clear filters
              </Button>
            </SheetFooter>
          </SheetContent>
        </Sheet>
        <p className="text-sm text-ink-2" aria-live="polite">
          {formatCount(total)} {total === 1 ? "match" : "matches"}
        </p>
      </div>
      {chips.length ? (
        <ul aria-label="Active filters" className="mt-3 flex flex-wrap gap-2">
          {chips.map((chip) => (
            <li key={chip.key}>
              <button
                type="button"
                aria-label={`Remove ${chip.label}`}
                onClick={() => onChange(chip.remove)}
                className="inline-flex min-h-11 cursor-pointer items-center gap-1.5 rounded-control border border-ink bg-paper pr-2.5 pl-3 text-sm text-ink"
              >
                <span>{chip.label}</span>
                <XIcon aria-hidden="true" className="size-4" />
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
