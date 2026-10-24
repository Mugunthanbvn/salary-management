"use client";

import { cn } from "cn";

type Option<T extends string> = { value: T; label: string };

type SegmentedControlProps<T extends string> = {
  /** Names the group for screen readers: "Pay shown", "Period". */
  label: string;
  options: readonly Option<T>[];
  value: T;
  onChange: (value: T) => void;
  className?: string;
};

/**
 * Two or three mutually exclusive choices side by side (the Base/Total and Annual/Monthly
 * toggles, docs/13-frontend-ux.md §3.4): 1 px ink outline, the chosen one filled with ink.
 * Each is a toggle button with aria-pressed, 44 px tall.
 */
export function SegmentedControl<T extends string>({
  label,
  options,
  value,
  onChange,
  className,
}: SegmentedControlProps<T>) {
  return (
    <div
      role="group"
      aria-label={label}
      className={cn(
        "inline-flex rounded-control border border-ink bg-paper",
        className,
      )}
    >
      {options.map((option, index) => {
        const pressed = option.value === value;
        return (
          <button
            key={option.value}
            type="button"
            aria-pressed={pressed}
            onClick={() => onChange(option.value)}
            className={cn(
              "min-h-11 cursor-pointer px-3.5 text-sm whitespace-nowrap",
              index > 0 && "border-l border-ink",
              index === 0 && "rounded-l-control",
              index === options.length - 1 && "rounded-r-control",
              pressed
                ? "bg-ink font-bold text-paper"
                : "text-ink hover:bg-rule",
            )}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
