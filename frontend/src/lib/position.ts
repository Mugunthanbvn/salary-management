export function positionPercent(
  value: number | string,
  lo: number | string,
  hi: number | string,
): number {
  void [value, lo, hi];
  throw new Error("positionPercent is not implemented yet");
}

export function stripScale(
  band: { min: number; max: number },
  figures: (number | null)[],
): { lo: number; hi: number } {
  void [band, figures];
  throw new Error("stripScale is not implemented yet");
}
