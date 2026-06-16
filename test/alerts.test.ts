import { describe, it, expect } from 'vitest';
import { activeAlerts, normalizeAlert, loadAlerts, type CityAlert } from '../src/lib/alerts';

const mk = (over: Partial<CityAlert>): CityAlert => ({
  id: 'a',
  level: 'info',
  title: 'T',
  message: 'M',
  start: '2026-06-01',
  end: '2026-06-30',
  ...over,
});

describe('activeAlerts', () => {
  it('includes an alert active on the reference day', () => {
    expect(activeAlerts([mk({})], '2026-06-15').map((a) => a.id)).toEqual(['a']);
  });

  it('includes alerts on their exact start and end boundaries (inclusive)', () => {
    const a = mk({ id: 'a', start: '2026-06-10', end: '2026-06-12' });
    expect(activeAlerts([a], '2026-06-10')).toHaveLength(1);
    expect(activeAlerts([a], '2026-06-12')).toHaveLength(1);
  });

  it('excludes alerts before start or after end', () => {
    const a = mk({ start: '2026-06-10', end: '2026-06-12' });
    expect(activeAlerts([a], '2026-06-09')).toHaveLength(0);
    expect(activeAlerts([a], '2026-06-13')).toHaveLength(0);
  });

  it('orders emergency before warning before info', () => {
    const list = [
      mk({ id: 'i', level: 'info' }),
      mk({ id: 'e', level: 'emergency' }),
      mk({ id: 'w', level: 'warning' }),
    ];
    expect(activeAlerts(list, '2026-06-15').map((a) => a.id)).toEqual(['e', 'w', 'i']);
  });

  it('preserves input order among same-level alerts (stable)', () => {
    const list = [mk({ id: 'x', level: 'info' }), mk({ id: 'y', level: 'info' })];
    expect(activeAlerts(list, '2026-06-15').map((a) => a.id)).toEqual(['x', 'y']);
  });

  it('filters out dismissed ids', () => {
    const list = [mk({ id: 'a' }), mk({ id: 'b' })];
    expect(activeAlerts(list, '2026-06-15', new Set(['a'])).map((x) => x.id)).toEqual(['b']);
  });

  it('returns an empty array for an empty list', () => {
    expect(activeAlerts([], '2026-06-15')).toEqual([]);
  });
});

describe('normalizeAlert', () => {
  it('builds a link object from the live linkHref string', () => {
    const out = normalizeAlert({
      id: 3,
      level: 'warning',
      title: 'Water main',
      message: 'Lane closures',
      start: '2026-06-15',
      end: '2026-06-25',
      linkHref: 'https://www.burtonmi.gov',
    });
    expect(out).toEqual({
      id: '3',
      level: 'warning',
      title: 'Water main',
      message: 'Lane closures',
      start: '2026-06-15',
      end: '2026-06-25',
      link: { text: 'More information', href: 'https://www.burtonmi.gov' },
    });
  });

  it('keeps an existing link object (committed alerts.json shape)', () => {
    const out = normalizeAlert({
      id: 'a',
      level: 'info',
      title: 'T',
      message: 'M',
      start: '2026-06-01',
      end: '2026-06-30',
      link: { text: 'Details', href: 'https://x' },
    });
    expect(out.link).toEqual({ text: 'Details', href: 'https://x' });
  });

  it('omits link when neither linkHref nor link is present (or href is empty)', () => {
    expect(normalizeAlert({ id: 'a', level: 'info', title: 'T', message: 'M', start: '2026-06-01', end: '2026-06-30', linkHref: '' }).link).toBeUndefined();
    expect(normalizeAlert({ id: 'b', level: 'info', title: 'T', message: 'M', start: '2026-06-01', end: '2026-06-30' }).link).toBeUndefined();
  });

  it('coerces id to string and defaults an unknown level to info', () => {
    const out = normalizeAlert({ id: 7, level: 'bogus', title: 'T', message: 'M', start: '2026-06-01', end: '2026-06-30' });
    expect(out.id).toBe('7');
    expect(out.level).toBe('info');
  });
});

describe('loadAlerts', () => {
  const live = { alerts: [{ id: 1, level: 'emergency', title: 'Boil water', message: 'Advisory', start: '2026-06-15', end: '2026-06-20', linkHref: '' }] };
  const file = { alerts: [{ id: 'f', level: 'info', title: 'F', message: 'from file', start: '2026-06-01', end: '2026-06-30' }] };
  const okResp = (body: unknown) => ({ ok: true, json: async () => body });

  it('returns normalized live alerts when the live endpoint is OK', async () => {
    const f = (async (u: string) => (u === 'https://flow/banner' ? okResp(live) : okResp(file))) as unknown as typeof fetch;
    const out = await loadAlerts('https://flow/banner', f);
    expect(out).toHaveLength(1);
    expect(out[0]).toMatchObject({ id: '1', level: 'emergency', title: 'Boil water' });
  });

  it('falls back to alerts.json when the live fetch throws', async () => {
    const f = (async (u: string) => {
      if (u === 'https://flow/banner') throw new Error('net');
      return okResp(file);
    }) as unknown as typeof fetch;
    const out = await loadAlerts('https://flow/banner', f);
    expect(out.map((a) => a.id)).toEqual(['f']);
  });

  it('falls back to alerts.json when the live response is not OK', async () => {
    const f = (async (u: string) => (u === 'https://flow/banner' ? { ok: false, json: async () => ({}) } : okResp(file))) as unknown as typeof fetch;
    const out = await loadAlerts('https://flow/banner', f);
    expect(out.map((a) => a.id)).toEqual(['f']);
  });

  it('uses alerts.json directly when no live URL is configured', async () => {
    const f = (async () => okResp(file)) as unknown as typeof fetch;
    const out = await loadAlerts(undefined, f);
    expect(out.map((a) => a.id)).toEqual(['f']);
  });

  it('returns [] when both sources fail', async () => {
    const f = (async () => {
      throw new Error('offline');
    }) as unknown as typeof fetch;
    expect(await loadAlerts('https://flow/banner', f)).toEqual([]);
  });
});
