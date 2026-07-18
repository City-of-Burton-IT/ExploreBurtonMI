import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { validateWasteSchedule } from '../src/lib/guide/wasteSchedule';

describe('waste schedule validation', () => {
  it('accepts the committed schedule', () => {
    const raw = JSON.parse(readFileSync('public/waste-schedule.json', 'utf8'));
    const expected = new Set(
      raw.entries.map((entry: { street: string; day: string }) => JSON.stringify([entry.street, entry.day])),
    );
    expect(validateWasteSchedule(raw)).toHaveLength(expected.size);
  });

  it('normalizes exact duplicates before the keyed result list renders', () => {
    const entry = { street: 'Sycamore North', day: 'Friday' };
    expect(validateWasteSchedule({ entries: [entry, entry] })).toEqual([entry]);
  });

  it.each([
    null,
    {},
    { entries: [] },
    { entries: [{ street: '', day: 'Monday' }] },
    { entries: [{ street: 'Main St', day: 'Saturday' }] },
    { entries: ['Main St'] },
  ])('rejects malformed schedule data: %j', (raw) => {
    expect(() => validateWasteSchedule(raw)).toThrow(/waste-schedule|entries/i);
  });
});
