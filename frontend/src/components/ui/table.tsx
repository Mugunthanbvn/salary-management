import * as React from "react";
import { cn } from "cn";

// The table parts, restyled to the printout: ink header rule, 1 px row rules, no fills.
// Layout only; the data model comes from TanStack Table in the component that uses them.

function Table({ className, ...props }: React.ComponentProps<"table">) {
  return (
    <table
      data-slot="table"
      className={cn("w-full border-collapse text-[15px]", className)}
      {...props}
    />
  );
}

function TableHeader({ className, ...props }: React.ComponentProps<"thead">) {
  return <thead data-slot="table-header" className={className} {...props} />;
}

function TableBody({ className, ...props }: React.ComponentProps<"tbody">) {
  return <tbody data-slot="table-body" className={className} {...props} />;
}

function TableRow({ className, ...props }: React.ComponentProps<"tr">) {
  return (
    <tr
      data-slot="table-row"
      className={cn("border-b border-rule", className)}
      {...props}
    />
  );
}

function TableHead({ className, ...props }: React.ComponentProps<"th">) {
  return (
    <th
      data-slot="table-head"
      className={cn(
        "pb-2.5 text-left align-bottom text-[13px] font-normal text-ink-2",
        className,
      )}
      {...props}
    />
  );
}

function TableCell({ className, ...props }: React.ComponentProps<"td">) {
  return (
    <td data-slot="table-cell" className={cn("py-3.5", className)} {...props} />
  );
}

function TableCaption({
  className,
  ...props
}: React.ComponentProps<"caption">) {
  return <caption data-slot="table-caption" className={className} {...props} />;
}

export {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
  TableCaption,
};
