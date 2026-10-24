import * as React from "react";
import { cn } from "cn";
import { ChevronDownIcon } from "lucide-react";

// The browser's own select, restyled to the printout: 44 px tall, 16 px text (no zoom on
// iOS focus), 1 px ink outline with 4 px corners. On phones it opens the system picker.
// `className` sizes the wrapper; every other prop goes to the <select>. An invalid field
// (aria-invalid) gets a 2 px red-pen border; link its message with aria-describedby.

function NativeSelect({ className, ...props }: React.ComponentProps<"select">) {
  return (
    <div
      className={cn(
        "relative w-full has-[select:disabled]:opacity-50",
        className,
      )}
      data-slot="native-select-wrapper"
    >
      <select
        data-slot="native-select"
        className="h-11 w-full min-w-0 cursor-pointer appearance-none truncate rounded-control border border-ink bg-paper py-0 pr-10 pl-3 text-base text-ink disabled:cursor-not-allowed aria-invalid:border-2 aria-invalid:border-red-pen"
        {...props}
      />
      <ChevronDownIcon
        className="pointer-events-none absolute top-1/2 right-3 size-5 -translate-y-1/2 text-ink-2"
        aria-hidden="true"
        data-slot="native-select-icon"
      />
    </div>
  );
}

function NativeSelectOption(props: React.ComponentProps<"option">) {
  return <option data-slot="native-select-option" {...props} />;
}

function NativeSelectOptGroup(props: React.ComponentProps<"optgroup">) {
  return <optgroup data-slot="native-select-optgroup" {...props} />;
}

export { NativeSelect, NativeSelectOptGroup, NativeSelectOption };
