const formatters = new Map<string, Intl.NumberFormat>();

/**
 * An Intl.NumberFormat for these options, built once and reused: building one costs about
 * 75 µs, which adds up across a table of amounts. The set of options in use is small
 * (a few locales × currencies × digits), so the cache stays small.
 */
export function numberFormat(
  locale: string,
  options: Intl.NumberFormatOptions,
): Intl.NumberFormat {
  const key = `${locale}|${JSON.stringify(options)}`;
  let formatter = formatters.get(key);
  if (!formatter) {
    formatter = new Intl.NumberFormat(locale, options);
    formatters.set(key, formatter);
  }
  return formatter;
}
