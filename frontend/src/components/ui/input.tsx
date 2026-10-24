import * as React from "react";
import { cn } from "cn";

// 44 px tall, 16 px text (no zoom on iOS focus), 1 px ink outline with 4 px corners.
// An invalid field (aria-invalid) gets a 2 px red-pen border; link its message with
// aria-describedby.
function Input({ className, type, ...props }: React.ComponentProps<"input">) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        "h-11 w-full min-w-0 rounded-control border border-ink bg-paper px-3 text-base text-ink placeholder:text-ink-3 disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-2 aria-invalid:border-red-pen",
        className,
      )}
      {...props}
    />
  );
}

export { Input };
