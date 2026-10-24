"use client";

export function ErrorState(props: {
  title: string;
  detail?: string | null;
  requestId?: string | null;
  onRetry?: () => void;
}) {
  void props;
  return null;
}
