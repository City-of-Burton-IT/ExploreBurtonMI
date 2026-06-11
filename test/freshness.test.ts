import { describe, it, expect } from 'vitest';
import { formatDataAsOf } from '../src/lib/freshness';

describe('formatDataAsOf', () => {
  it('formats a full ISO date as "Month YYYY"', () => {
    expect(formatDataAsOf('2026-06-11')).toBe('June 2026');
  });

  it('formats a year-month value as "Month YYYY"', () => {
    expect(formatDataAsOf('2026-01')).toBe('January 2026');
  });

  it('does not roll a year-end date into the next year (UTC, not local tz)', () => {
    expect(formatDataAsOf('2026-12-31')).toBe('December 2026');
  });

  it('returns null for an empty string', () => {
    expect(formatDataAsOf('')).toBeNull();
  });

  it('returns null for a non-date string', () => {
    expect(formatDataAsOf('not-a-date')).toBeNull();
  });

  it('returns null for null/undefined', () => {
    expect(formatDataAsOf(undefined)).toBeNull();
    expect(formatDataAsOf(null)).toBeNull();
  });
});
