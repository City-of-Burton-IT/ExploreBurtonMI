import { describe, it, expect } from 'vitest';
import { nextMeetingDate } from '../src/lib/guide/nextMeeting';

const M = [{ date: '2026-01-08' }, { date: '2026-01-22' }, { date: '2026-02-02' }];

describe('nextMeetingDate', () => {
  it('returns the first meeting on or after the reference date', () => {
    expect(nextMeetingDate(M, '2026-01-10')).toBe('2026-01-22');
  });
  it('includes a meeting that is exactly the reference date', () => {
    expect(nextMeetingDate(M, '2026-01-22')).toBe('2026-01-22');
  });
  it('returns the earliest when the reference precedes all', () => {
    expect(nextMeetingDate(M, '2025-12-01')).toBe('2026-01-08');
  });
  it('returns null when every meeting is in the past', () => {
    expect(nextMeetingDate(M, '2026-03-01')).toBeNull();
  });
  it('returns null for an empty list', () => {
    expect(nextMeetingDate([], '2026-01-01')).toBeNull();
  });
});
