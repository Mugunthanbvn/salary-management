"use client";

import { ErrorState } from "@/components/print";

/**
 * Shown inside the shell when a page throws. In production Next sends the browser only a
 * generic message for errors thrown on the server, so this never shows `error.message`.
 * A page that wants to show the API's problem renders <ErrorState> itself instead.
 */
export default function AppError({
  retry,
}: {
  error: unknown;
  retry: () => void;
}) {
  return (
    <ErrorState
      title="This page couldn't load"
      detail="Something went wrong on our side. Try again, or come back in a few minutes."
      onRetry={retry}
    />
  );
}
