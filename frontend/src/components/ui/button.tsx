import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "cn";
import { Slot } from "radix-ui";

// DESIGN.md: primary = ink fill, secondary = 1 px ink outline, destructive = red-pen text.
// Every size is at least 44 px tall, the touch-target minimum.
const buttonVariants = cva(
  "inline-flex shrink-0 cursor-pointer items-center justify-center gap-2 rounded-control border text-[15px] font-bold whitespace-nowrap transition-colors select-none disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-5",
  {
    variants: {
      variant: {
        primary:
          "border-ink bg-ink text-paper hover:border-ink-2 hover:bg-ink-2",
        secondary: "border-ink bg-paper text-ink hover:bg-rule",
        destructive:
          "border-transparent bg-transparent text-red-pen underline-offset-4 hover:underline",
        ghost: "border-transparent bg-transparent text-ink hover:bg-rule",
        link: "border-transparent bg-transparent px-0 font-normal text-blue-pen underline underline-offset-4 hover:text-blue-pen-hover",
      },
      size: {
        default: "min-h-11 px-4",
        icon: "size-11",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "default",
    },
  },
);

function Button({
  className,
  variant = "primary",
  size = "default",
  asChild = false,
  ...props
}: React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean;
  }) {
  const Comp = asChild ? Slot.Root : "button";

  return (
    <Comp
      data-slot="button"
      data-variant={variant}
      data-size={size}
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  );
}

export { Button, buttonVariants };
