import { describe, it, expect } from 'vitest';
import { activeOpsItems, statusMeta, type OpsItem } from '../src/lib/guide/opsStatus';

const mk = (over: Partial<OpsItem>): OpsItem => ({
  id: 'x',
  service: 'Leaf pickup',
  status: 'standby',
  detail: 'd',
  active: true,
  ...over,
});

describe('activeOpsItems', () => {
  it('keeps only active items, in file order', () => {
    const items = [
      mk({ id: 'a', active: false }),
      mk({ id: 'b', active: true }),
      mk({ id: 'c', active: true }),
    ];
    expect(activeOpsItems(items).map((i) => i.id)).toEqual(['b', 'c']);
  });

  it('returns an empty array when none are active', () => {
    expect(activeOpsItems([mk({ active: false })])).toEqual([]);
  });

  it('returns an empty array for an empty list', () => {
    expect(activeOpsItems([])).toEqual([]);
  });
});

describe('statusMeta', () => {
  it('maps each known status to a label, colour, and icon', () => {
    expect(statusMeta('in-progress')).toEqual({ label: 'In progress', color: '#1d7f2b', icon: 'in-progress' });
    expect(statusMeta('scheduled').label).toBe('Scheduled');
    expect(statusMeta('complete').label).toBe('Complete');
    expect(statusMeta('standby').label).toBe('Standby');
  });

  it('falls back to a neutral standby look for an unknown status', () => {
    const m = statusMeta('frobnicating');
    expect(m.icon).toBe('standby');
    expect(m.label).toBe('frobnicating');
    expect(m.color).toBe('#6b7280');
  });
});
