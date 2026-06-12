import { describe, it, expect } from 'vitest';
import { placeIdFromHash, placeHash, placeShareUrl, SITE_BASE } from '../src/lib/hash';

describe('placeIdFromHash', () => {
  it('extracts the id from a place permalink', () => {
    expect(placeIdFromHash('#map/place/abc-123')).toBe('abc-123');
  });
  it('decodes a percent-encoded id', () => {
    expect(placeIdFromHash('#map/place/a%20b')).toBe('a b');
  });
  it('returns null for non-place hashes', () => {
    expect(placeIdFromHash('#finances')).toBeNull();
    expect(placeIdFromHash('#map')).toBeNull();
    expect(placeIdFromHash('#guide/trash')).toBeNull();
    expect(placeIdFromHash('')).toBeNull();
  });
});

describe('placeHash', () => {
  it('builds a place hash and round-trips with placeIdFromHash', () => {
    expect(placeHash('abc-123')).toBe('map/place/abc-123');
    expect(placeIdFromHash('#' + placeHash('a b'))).toBe('a b');
  });
});

describe('placeShareUrl (#53 -- canonical, never localhost/capacitor)', () => {
  it('builds a full live-site URL from the place id', () => {
    expect(placeShareUrl('abc-123')).toBe('https://explore.burtonmi.gov/#map/place/abc-123');
  });
  it('uses the canonical SITE_BASE origin', () => {
    expect(SITE_BASE).toBe('https://explore.burtonmi.gov/');
    expect(placeShareUrl('x').startsWith(SITE_BASE)).toBe(true);
  });
  it('percent-encodes ids in the shared URL', () => {
    expect(placeShareUrl('a b')).toBe('https://explore.burtonmi.gov/#map/place/a%20b');
  });
});
