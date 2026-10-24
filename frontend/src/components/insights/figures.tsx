"use client";

export const HIDDEN_REASON =
  "Hidden to protect individual pay (fewer than 5 people)";

export function Hidden() {
  throw new Error("Hidden is not implemented yet");
}

export function PeriodMoney(props: {
  amountMinor: number | null;
  currency: string;
}) {
  void props;
  throw new Error("PeriodMoney is not implemented yet");
}
