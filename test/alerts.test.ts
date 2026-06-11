import { describe, it, expect } from 'vitest';
import { activeAlerts, type CityAlert } from '../src/lib/alerts';

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
