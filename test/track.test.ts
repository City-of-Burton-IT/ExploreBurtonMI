import { describe, it, expect } from 'vitest';
import { newToken, stageFor } from '../src/lib/track';

describe('newToken', () => {
  it('is url-safe and high-entropy (>= 22 chars, [A-Za-z0-9_-])', () => {
    const t = newToken();
    expect(t).toMatch(/^[A-Za-z0-9_-]{22,}$/);
  });
  it('is unique across calls', () => {
    const set = new Set(Array.from({ length: 1000 }, () => newToken()));
    expect(set.size).toBe(1000);
  });
});

describe('stageFor', () => {
  it('maps report statuses', () => {
    expect(stageFor('report', 'New')).toBe('Received');
    expect(stageFor('report', 'In progress')).toBe('In progress');
    expect(stageFor('report', 'Closed')).toBe('Resolved');
  });
  it('maps listing statuses', () => {
    expect(stageFor('listing', 'New')).toBe('Received');
    expect(stageFor('listing', 'Approved')).toBe('Approved & published');
    expect(stageFor('listing', 'Applied')).toBe('Approved & published');
    expect(stageFor('listing', 'Rejected')).toBe('Not accepted');
    expect(stageFor('listing', 'Needs-info')).toBe('Needs more info');
  });
  it('falls back to "In review" for unknown/empty', () => {
    expect(stageFor('report', 'Whatever')).toBe('In review');
    expect(stageFor('listing', '')).toBe('In review');
  });
});
