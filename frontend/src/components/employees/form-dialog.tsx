"use client";

import { cn } from "cn";
import { XIcon } from "lucide-react";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { fieldErrors, type PlainProblem } from "@/lib/api/action-result";

type FormDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: ReactNode;
  submitLabel: string;
  pendingLabel: string;
  pending: boolean;
  onSubmit: () => void;
  /** A wider dialog from 640 px, for forms with rows of fields. */
  wide?: boolean;
  /** The submit button in red-pen: an action that is hard to undo. */
  destructive?: boolean;
  children: ReactNode;
};

/**
 * A form in a dialog: centred from 640 px, full screen on a phone with the title and the
 * buttons always in view (sticky header and footer, docs/13-frontend-ux.md §8).
 */
export function FormDialog({
  open,
  onOpenChange,
  title,
  description,
  submitLabel,
  pendingLabel,
  pending,
  onSubmit,
  wide = false,
  destructive = false,
  children,
}: FormDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        showCloseButton={false}
        className={cn("gap-0 p-0 pt-0 pb-0 sm:p-0", wide && "sm:max-w-2xl")}
      >
        <form
          noValidate
          onSubmit={(event) => {
            event.preventDefault();
            onSubmit();
          }}
          className="flex min-h-full flex-col"
        >
          <DialogHeader className="sticky top-0 z-10 border-b border-rule bg-paper px-4 pt-[max(1rem,env(safe-area-inset-top))] pb-4 sm:px-6 sm:pt-5">
            <DialogTitle>{title}</DialogTitle>
            {description ? (
              <DialogDescription>{description}</DialogDescription>
            ) : null}
            <DialogClose asChild>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="absolute top-[max(0.5rem,env(safe-area-inset-top))] right-2 sm:top-3"
              >
                <XIcon aria-hidden="true" />
                <span className="sr-only">Close</span>
              </Button>
            </DialogClose>
          </DialogHeader>
          <div className="flex flex-1 flex-col gap-5 px-4 py-5 sm:px-6">
            {children}
          </div>
          <DialogFooter className="sticky bottom-0 z-10 border-t border-rule bg-paper px-4 pt-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] sm:px-6 sm:pb-4">
            <DialogClose asChild>
              <Button type="button" variant="secondary">
                Cancel
              </Button>
            </DialogClose>
            <Button
              type="submit"
              disabled={pending}
              className={cn(
                destructive &&
                  "border-red-pen bg-red-pen hover:border-red-pen hover:bg-red-pen hover:underline",
              )}
            >
              {pending ? pendingLabel : submitLabel}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export const VERSION_CONFLICT =
  "This employee was changed by someone else. Reload to see their changes.";

/**
 * What went wrong with the last submit, announced to screen readers: a version conflict
 * with a Reload button, field errors that have no field of their own, or the API's problem
 * with its request id.
 */
export function FormProblem({
  problem,
  unmatched,
  onReload,
}: {
  problem: PlainProblem | null;
  /** Field errors no field on the form shows. */
  unmatched: string[];
  onReload: () => void;
}) {
  if (!problem) return null;
  const box = "border-t-2 border-red-pen pt-3 text-[15px] text-ink";
  if (problem.slug === "version-conflict") {
    return (
      <div role="alert" className={box}>
        <p>{VERSION_CONFLICT}</p>
        <Button
          type="button"
          variant="secondary"
          className="mt-3"
          onClick={onReload}
        >
          Reload
        </Button>
      </div>
    );
  }
  // A duplicate the form can show at its field reads like a validation error.
  const atField =
    problem.slug === "duplicate" &&
    Object.keys(fieldErrors(problem)).length > 0;
  if (problem.slug === "validation" || atField) {
    return (
      <div role="alert" className={box}>
        <p className="font-bold">Some details need fixing.</p>
        {unmatched.length ? (
          <ul className="mt-1 list-disc pl-5">
            {unmatched.map((message) => (
              <li key={message}>{message}</li>
            ))}
          </ul>
        ) : null}
      </div>
    );
  }
  return (
    <div role="alert" className={box}>
      <p className="font-bold">{problem.title}</p>
      {problem.detail ? <p className="mt-1">{problem.detail}</p> : null}
      {problem.requestId ? (
        <p className="mt-1 text-sm text-ink-3">
          Request ID: {problem.requestId}
        </p>
      ) : null}
    </div>
  );
}

/** The field's error under it, linked with aria-describedby by the caller. */
export function FieldError({ id, message }: { id: string; message?: string }) {
  if (!message) return null;
  return (
    <p id={id} className="text-sm text-red-pen">
      {message}
    </p>
  );
}

/** Props that mark a field invalid and point it at its error message. */
export function invalidProps(id: string, message?: string) {
  return message
    ? { "aria-invalid": true as const, "aria-describedby": id }
    : {};
}

/** The field errors no field shows, for <FormProblem>. */
export function unmatchedErrors(
  errors: Record<string, string>,
  shown: (key: string) => boolean,
): string[] {
  return Object.entries(errors)
    .filter(([key]) => !shown(key))
    .map(([, message]) => message);
}
