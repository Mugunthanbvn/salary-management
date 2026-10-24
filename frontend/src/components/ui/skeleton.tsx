import { cn } from "cn";

// A grey block in the shape of the content that is loading. Hidden from screen readers:
// put the loading message on the surrounding region (aria-busy, or a visually hidden text).
function Skeleton({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="skeleton"
      aria-hidden="true"
      className={cn("animate-pulse bg-rule", className)}
      {...props}
    />
  );
}

export { Skeleton };
