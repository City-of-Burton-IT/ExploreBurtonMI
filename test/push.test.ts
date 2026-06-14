import { describe, it, expect } from 'vitest';
import { PUSH_TOPICS, parsePrefs, serializePrefs } from '../src/lib/push';

describe('PUSH_TOPICS', () => {
  it('is the three decided categories', () => {
    expect(PUSH_TOPICS.map((t) => t.id)).toEqual(['alerts', 'service', 'meetings']);
  });
});

describe('parsePrefs', () => {
  it('returns an empty set for null/empty/garbage', () => {
    expect(parsePrefs(null).size).toBe(0);
    expect(parsePrefs('').size).toBe(0);
    expect(parsePrefs('not json').size).toBe(0);
    expect(parsePrefs('{"a":1}').size).toBe(0); // not an array
  });

  it('keeps only known topic ids', () => {
    const prefs = parsePrefs('["alerts","meetings","bogus","marketing"]');
    expect([...prefs].sort()).toEqual(['alerts', 'meetings']);
  });

  it('ignores non-string array members', () => {
    const prefs = parsePrefs('["service", 5, null, {"x":1}]');
    expect([...prefs]).toEqual(['service']);
  });
});

describe('serializePrefs', () => {
  it('round-trips through parsePrefs', () => {
    const out = serializePrefs(new Set(['meetings', 'alerts']));
    expect([...parsePrefs(out).values()].sort()).toEqual(['alerts', 'meetings']);
  });

  it('is sorted + filtered to known topics for stable output', () => {
    expect(serializePrefs(new Set(['service', 'alerts', 'nope']))).toBe('["alerts","service"]');
  });
});
