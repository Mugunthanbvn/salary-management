/**
 * Display geometry for band strips and bars: where an API figure sits along a scale, as a
 * CSS percentage. It only places marks on screen; every figure itself comes from the API
 * and is shown with lib/money.ts or lib/numbers.ts, never with these numbers.
 */

/** `value` along `lo`…`hi` as 0–100 (clamped); decimal-string ratios are read too. */
export function positionPercent(
  value: number | string,
  lo: number | string,
  hi: number | string,
): number {
  const [v, from, to] = [Number(value), Number(lo), Number(hi)];
  if (to <= from) return 50;
  const percent = ((v - from) / (to - from)) * 100;
  return Math.min(100, Math.max(0, percent));
}

/**
 * The scale for one cohort's strip: its band's min–max, widened to take in any of the
 * cohort's figures (P25, median, P75) that fall outside the band. Hidden figures (null)
 * are left out.
 */
export function stripScale(
  band: { min: number; max: number },
  figures: (number | null)[],
): { lo: number; hi: number } {
  const shown = figures.filter((figure): figure is number => figure !== null);
  return {
    lo: Math.min(band.min, ...shown),
    hi: Math.max(band.max, ...shown),
  };
}
