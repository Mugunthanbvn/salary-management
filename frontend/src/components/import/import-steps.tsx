import { cn } from "cn";

const STEPS = ["Upload", "Check", "Import"] as const;

/** "1. Upload  2. Check  3. Import", the current one underlined, as on the artboard. */
export function ImportSteps({ current }: { current: (typeof STEPS)[number] }) {
  return (
    <ol
      aria-label="Import steps"
      className="mb-6 flex flex-wrap gap-x-8 gap-y-2 text-[15px]"
    >
      {STEPS.map((step, index) => (
        <li
          key={step}
          aria-current={step === current ? "step" : undefined}
          className={cn(
            step === current
              ? "font-bold underline decoration-2 underline-offset-[6px]"
              : "text-ink-2",
          )}
        >
          {index + 1}. {step}
        </li>
      ))}
    </ol>
  );
}
