import type { ReactNode } from "react";

type PageTitleProps = {
  /** The page's question or name, in sentence case: "How ACME pays people". */
  title: string;
  /** One summary sentence under the title (a sentence, never KPI tiles). */
  children?: ReactNode;
  /** Page-level controls on the right, e.g. the Base/Total and Yearly/Monthly toggles. */
  actions?: ReactNode;
};

/** The title block every page starts with; it ends with a 2 px ink rule. */
export function PageTitle({ title, children, actions }: PageTitleProps) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-6 border-b-2 border-ink pb-6 sm:pb-8">
      <div className="min-w-0 flex-[999_1_560px]">
        <h1 className="font-serif text-[32px] leading-[1.1] font-semibold tracking-[-0.01em] sm:text-[48px]">
          {title}
        </h1>
        {children ? (
          <p className="mt-3 max-w-[640px] text-[15px] leading-normal text-ink-2 sm:text-[17px]">
            {children}
          </p>
        ) : null}
      </div>
      {actions ? <div className="flex flex-wrap gap-3">{actions}</div> : null}
    </div>
  );
}
