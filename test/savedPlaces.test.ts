import { describe, it, expect } from 'vitest';
import { loadSaved, serializeSaved, toggleSaved } from '../src/lib/savedPlaces';

describe('loadSaved', () => {
  it('returns an empty set for missing storage', () => {
    expect(loadSaved(null).size).toBe(0);
    expect(loadSaved('').size).toBe(0);
  });

  it('parses a stored array of ids', () => {
    const s = loadSaved('["a","b","c"]');
    expect([...s].sort()).toEqual(['a', 'b', 'c']);
  });

  it('drops non-string entries and survives corrupt JSON', () => {
    expect([...loadSaved('["a",1,null,"b"]')].sort()).toEqual(['a', 'b']);
    expect(loadSaved('not json').size).toBe(0);
    expect(loadSaved('{"a":1}').size).toBe(0); // not an array
  });
});

describe('serializeSaved / round-trip', () => {
  it('round-trips through localStorage form', () => {
    const ids = new Set(['x', 'y']);
    expect([...loadSaved(serializeSaved(ids))].sort()).toEqual(['x', 'y']);
  });
});

describe('toggleSaved', () => {
  it('adds an id when absent and returns a new set', () => {
    const a = new Set(['x']);
    const b = toggleSaved(a, 'y');
    expect(b).not.toBe(a);
    expect([...b].sort()).toEqual(['x', 'y']);
    expect([...a]).toEqual(['x']); // original untouched
  });

  it('removes an id when present', () => {
    expect([...toggleSaved(new Set(['x', 'y']), 'x')]).toEqual(['y']);
  });
});
