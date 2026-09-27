/** Mongolian date/time formatting — avoids English month names from incomplete mn-MN ICU. */

const MN_MONTHS = [
  "1-р сар",
  "2-р сар",
  "3-р сар",
  "4-р сар",
  "5-р сар",
  "6-р сар",
  "7-р сар",
  "8-р сар",
  "9-р сар",
  "10-р сар",
  "11-р сар",
  "12-р сар",
] as const;

function parseStamp(value: string | null | undefined): Date | null {
  if (!value) return null;
  const stamp = Date.parse(value);
  if (Number.isNaN(stamp)) return null;
  return new Date(stamp);
}

function pad2(n: number): string {
  return n < 10 ? `0${n}` : String(n);
}

/** e.g. 2026 оны 9-р сарын 26 */
export function formatDateMn(value: string | null | undefined): string {
  const date = parseStamp(value);
  if (!date) return value || "—";
  const year = date.getFullYear();
  const month = MN_MONTHS[date.getMonth()];
  const day = date.getDate();
  return `${year} оны ${month}ын ${day}`;
}

/**
 * Compact datetime for admin lists, e.g. 2026.09.26 16:55
 * Uses local timezone; 24-hour clock (no AM/PM English).
 */
export function formatDateTimeMn(value: string | null | undefined): string {
  const date = parseStamp(value);
  if (!date) return value || "—";
  const y = date.getFullYear();
  const m = pad2(date.getMonth() + 1);
  const d = pad2(date.getDate());
  const hh = pad2(date.getHours());
  const mm = pad2(date.getMinutes());
  return `${y}.${m}.${d} ${hh}:${mm}`;
}

/** Longer readable datetime, e.g. 2026 оны 9-р сарын 26, 16:55 */
export function formatDateTimeLongMn(value: string | null | undefined): string {
  const date = parseStamp(value);
  if (!date) return value || "—";
  const hh = pad2(date.getHours());
  const mm = pad2(date.getMinutes());
  return `${formatDateMn(value)}, ${hh}:${mm}`;
}
