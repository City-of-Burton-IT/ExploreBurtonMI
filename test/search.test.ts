import { describe, it, expect } from 'vitest';
import { buildIndex, searchIds } from '../src/lib/search';
import type { PlaceFeature } from '../src/lib/types';

const KEYS = ['name', 'category', 'address', 'description', 'services'];

function feature(id: string, props: Partial<PlaceFeature['properties']>): PlaceFeature {
  return {
    type: 'Feature',
    id,
    geometry: { type: 'Point', coordinates: [-83.6, 42.99] },
    properties: { name: id, ...props },
  };
}

const FEATURES: PlaceFeature[] = [
  feature('city-hall', {
    name: 'Burton City Hall',
    category: 'Government',
    address: '4303 S Center Rd',
    description: 'Municipal offices and city clerk.',
  }),
  feature('trash-park', {
    name: 'Trash Park',
    category: 'Parks',
    address: '123 Park Ave',
    description: 'A city park with a playground.',
  }),
  feature('big-box', {
    name: 'Big Box Store',
    category: ['Retail', 'Pharmacy'],
    address: '5000 Belsay Rd',
    services: ['Pharmacy', 'Auto Center'],
  }),
  feature('police-dept', {
    name: 'Burton Police Department',
    category: 'Public Safety',
    address: '4303 S Center Rd',
  }),
];

describe('buildIndex / searchIds', () => {
  it('returns null (sentinel: no search active) for queries under 2 chars', () => {
    const index = buildIndex(FEATURES, KEYS);
    expect(searchIds(index, '')).toBeNull();
    expect(searchIds(index, ' ')).toBeNull();
    expect(searchIds(index, 'a')).toBeNull();
  });

  it('finds features by a matching field value', () => {
    const index = buildIndex(FEATURES, KEYS);
    const ids = searchIds(index, 'park');
    expect(ids).not.toBeNull();
    expect(ids!.has('trash-park')).toBe(true);
  });

  it('does not confuse a substring match inside another word (park vs police)', () => {
    // Regression guard for the noisy-fuzzy-match problem the module's header
    // comment calls out ("park" matching "Police Department").
    const index = buildIndex(FEATURES, KEYS);
    const ids = searchIds(index, 'park');
    expect(ids!.has('police-dept')).toBe(false);
  });

  it('ANDs multi-word queries (both terms must match)', () => {
    const index = buildIndex(FEATURES, KEYS);
    const both = searchIds(index, 'burton police');
    expect(both!.has('police-dept')).toBe(true);
    expect(both!.size).toBe(1);

    // "burton" alone matches both city hall and the police dept.
    const justBurton = searchIds(index, 'burton');
    expect(justBurton!.has('city-hall')).toBe(true);
    expect(justBurton!.has('police-dept')).toBe(true);

    // Adding a term that only one of them has narrows the AND result.
    const narrowed = searchIds(index, 'burton clerk');
    expect(narrowed!.has('city-hall')).toBe(true);
    expect(narrowed!.has('police-dept')).toBe(false);
  });

  it('tolerates a 1-character typo (fuzzy matching)', () => {
    const index = buildIndex(FEATURES, KEYS);
    // "polioe" -> "police" (one substitution).
    const ids = searchIds(index, 'polioe');
    expect(ids!.has('police-dept')).toBe(true);
  });

  it('matches array-valued properties (category, services) by joining them', () => {
    const index = buildIndex(FEATURES, KEYS);
    expect(searchIds(index, 'pharmacy')!.has('big-box')).toBe(true);
    expect(searchIds(index, 'retail')!.has('big-box')).toBe(true);
  });

  it('supports prefix matching', () => {
    const index = buildIndex(FEATURES, KEYS);
    expect(searchIds(index, 'burt')!.has('city-hall')).toBe(true);
  });

  it('returns an empty set (not null) when nothing matches a real query', () => {
    const index = buildIndex(FEATURES, KEYS);
    const ids = searchIds(index, 'zzqqxx');
    expect(ids).not.toBeNull();
    expect(ids!.size).toBe(0);
  });
});
