/**
 * Shared utility functions.
 *
 * Keep utilities pure and side-effect-free.
 * Group by concern and split into separate files as the codebase grows.
 */

/**
 * Formats a Date (or ISO string) into a human-readable locale string.
 * Centralising this prevents scattered `toLocaleDateString` calls.
 */
export function formatDate(
  date: Date | string,
  locale: Intl.LocalesArgument = 'en-US',
  options: Intl.DateTimeFormatOptions = {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  },
): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleDateString(locale, options);
}

/**
 * Returns a copy of the object with all keys whose value is `undefined`
 * or `null` removed. Useful for cleaning API payloads.
 */
export function omitNullish<T extends Record<string, unknown>>(
  obj: T,
): Partial<T> {
  return Object.fromEntries(
    Object.entries(obj).filter(([, v]) => v != null),
  ) as Partial<T>;
}
