import * as React from "react";
import { cn } from "cn";

// Like Input: 16 px text, 1 px ink outline with 4 px corners; it grows with its text.
// An invalid field (aria-invalid) gets a 2 px red-pen border.
function Textarea({ className, ...props }: React.ComponentProps<"textarea">) {
  return (
    <textarea
      data-slot="textarea"
      className={cn(
        "flex field-sizing-content min-h-24 w-full rounded-control border border-ink bg-paper px-3 py-2 text-base text-ink placeholder:text-ink-3 disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-2 aria-invalid:border-red-pen",
        className,
      )}
      {...props}
    />
  );
}

export { Textarea };
