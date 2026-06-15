import { describe, it, expect } from 'vitest';
import { newToken, stageFor, fetchStatus } from '../src/lib/track';

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

describe('fetchStatus', () => {
  const url = 'https://flow.example/readstatus';
  it('returns a found result mapped to a stage', async () => {
    const res = {
      ok: true,
      json: async () => ({
        found: true,
        kind: 'report',
        status: 'In progress',
        updatedAt: '2026-06-15',
        recap: 'Pothole on X',
        publicNote: 'Scheduled',
      }),
    };
    const f = (async () => res) as unknown as typeof fetch;
    const out = await fetchStatus(url, 'tok', 'report', f);
    expect(out).toEqual({
      found: true,
      stage: 'In progress',
      updatedAt: '2026-06-15',
      recap: 'Pothole on X',
      publicNote: 'Scheduled',
    });
  });
  it('returns {found:false} for an unknown token', async () => {
    const res = { ok: true, json: async () => ({ found: false }) };
    const f = (async () => res) as unknown as typeof fetch;
    expect(await fetchStatus(url, 'bad', 'report', f)).toEqual({ found: false });
  });
  it('returns {found:false} on network/parse error', async () => {
    const f = (async () => {
      throw new Error('net');
    }) as unknown as typeof fetch;
    expect(await fetchStatus(url, 'tok', 'report', f)).toEqual({ found: false });
  });
});
