import { readFileSync } from 'node:fs';
import { describe, it, expect } from 'vitest';
import { activeOpsItems, statusMeta, validateOpsStatusBundle, type OpsItem } from '../src/lib/guide/opsStatus';

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

describe('validateOpsStatusBundle', () => {
  const valid = { updated: '2026-06-11', items: [mk({})] };

  it('accepts a valid bundle', () => {
    expect(() => validateOpsStatusBundle(valid)).not.toThrow();
  });

  it('accepts the real public/ops-status.json', () => {
    const raw = JSON.parse(readFileSync('public/ops-status.json', 'utf-8'));
    expect(() => validateOpsStatusBundle(raw)).not.toThrow();
  });

  it('accepts a bundle without the optional updated field', () => {
    expect(() => validateOpsStatusBundle({ items: [mk({})] })).not.toThrow();
  });

  it('throws when not an object', () => {
    expect(() => validateOpsStatusBundle(null)).toThrow(/object/);
  });

  it('throws when items is not an array', () => {
    expect(() => validateOpsStatusBundle({ items: 'nope' })).toThrow(/items/);
  });

  it('throws when an item is missing required fields', () => {
    const bad = { items: [{ id: 'x', service: 'y' }] };
    expect(() => validateOpsStatusBundle(bad)).toThrow(/status/);
  });

  it('throws when an item.active is not a boolean', () => {
    const bad = { items: [{ ...mk({}), active: 'yes' }] };
    expect(() => validateOpsStatusBundle(bad)).toThrow(/active/);
  });
});
