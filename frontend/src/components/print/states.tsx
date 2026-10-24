import type { ReactNode } from "react";

export function EmptyState(props: {
  title: string;
  children?: ReactNode;
  action?: ReactNode;
}) {
  void props;
  return null;
}

export function Forbidden() {
  return null;
}
