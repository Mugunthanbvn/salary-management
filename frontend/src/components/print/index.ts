// The "Marked-up printout" building blocks (docs/design/DESIGN.md). See README.md here.
import type { ReactNode } from "react";

export { PageTitle } from "./page-title";
export { Section } from "./section";

// Not built yet: stubs so the marks test compiles.
export function Highlight(props: { children: ReactNode }) {
  void props;
  return null;
}
export function RedPen(props: { children: ReactNode }) {
  void props;
  return null;
}
export function MarginNote(props: { children: ReactNode }) {
  void props;
  return null;
}
export function StatusWord(props: {
  tone: "problem" | "notice" | "plain";
  children: ReactNode;
}) {
  void props;
  return null;
}
export function Money(props: { amountMinor: number; currency: string }) {
  void props;
  return null;
}
