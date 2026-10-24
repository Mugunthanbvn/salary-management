export type MinorUnitsResult =
  { ok: true; minor: number } | { ok: false; message: string };

export function toMinorUnits(
  input: string,
  currency: string,
  exponent: number,
): MinorUnitsResult {
  void [input, currency, exponent];
  throw new Error("toMinorUnits is not implemented yet");
}

export function toMajorInput(minor: number, exponent: number): string {
  void [minor, exponent];
  throw new Error("toMajorInput is not implemented yet");
}
