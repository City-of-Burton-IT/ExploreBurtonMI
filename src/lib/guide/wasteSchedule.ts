export interface WasteScheduleEntry {
  street: string;
  day: 'Monday' | 'Tuesday' | 'Wednesday' | 'Thursday' | 'Friday';
}

const PICKUP_DAYS = new Set<WasteScheduleEntry['day']>([
  'Monday',
  'Tuesday',
  'Wednesday',
  'Thursday',
  'Friday',
]);

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export function validateWasteSchedule(raw: unknown): WasteScheduleEntry[] {
  if (!isObject(raw) || !Array.isArray(raw.entries)) {
    throw new Error('waste-schedule.json entries must be an array');
  }
  const errors: string[] = [];
  const seen = new Set<string>();
  const entries: WasteScheduleEntry[] = [];
  raw.entries.forEach((entry, index) => {
    if (!isObject(entry)) {
      errors.push(`entries[${index}] is not an object`);
      return;
    }
    const street = typeof entry.street === 'string' ? entry.street.trim() : '';
    const day = entry.day;
    if (!street) errors.push(`entries[${index}].street is required`);
    if (typeof day !== 'string' || !PICKUP_DAYS.has(day as WasteScheduleEntry['day'])) {
      errors.push(`entries[${index}].day is not a weekday pickup day`);
    }
    if (street && typeof day === 'string' && PICKUP_DAYS.has(day as WasteScheduleEntry['day'])) {
      const key = JSON.stringify([street, day]);
      if (!seen.has(key)) {
        seen.add(key);
        entries.push({ street, day: day as WasteScheduleEntry['day'] });
      }
    }
  });
  if (entries.length === 0) errors.push('entries must contain at least one street');
  if (errors.length) throw new Error(`Invalid waste-schedule.json:\n - ${errors.join('\n - ')}`);
  return entries;
}
