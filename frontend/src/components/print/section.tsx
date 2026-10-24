import { useId, type ReactNode } from "react";

type SectionProps = {
  /** The question HR is asking, in sentence case: "Is anyone paid unfairly?" */
  question: string;
  /** The answer: a sentence, a table or a list. */
  children: ReactNode;
};

/**
 * One row of the printout: the question on the left (flex 1 1 280px), the answer on the
 * right (flex 999 1 640px). Below about 960 px the question stacks above the answer.
 * Sections are split by 1 px rules.
 */
export function Section({ question, children }: SectionProps) {
  const headingId = useId();
  return (
    <section
      aria-labelledby={headingId}
      className="flex flex-wrap gap-x-12 gap-y-4 border-b border-rule py-8 last:border-b-0 sm:gap-y-6 sm:py-10"
    >
      <h2
        id={headingId}
        className="min-w-0 flex-[1_1_280px] font-serif text-[22px] leading-tight font-semibold sm:text-[28px]"
      >
        {question}
      </h2>
      <div className="min-w-0 flex-[999_1_640px]">{children}</div>
    </section>
  );
}
