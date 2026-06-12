import { describe, it, expect } from 'vitest';
import { routeFromUrl } from '../src/lib/deepLinks';

describe('routeFromUrl (Android App Link -> in-app hash route)', () => {
  it('maps a dashboard fragment to its route', () => {
    expect(routeFromUrl('https://explore.burtonmi.gov/#finances')).toBe('finances');
  });

  it('maps a guide-section fragment', () => {
    expect(routeFromUrl('https://explore.burtonmi.gov/#guide/pickup-schedule')).toBe(
      'guide/pickup-schedule',
    );
  });

  it('maps a place permalink fragment', () => {
    expect(routeFromUrl('https://explore.burtonmi.gov/#map/place/abc-123')).toBe(
      'map/place/abc-123',
    );
  });

  it('returns empty (the map) for the bare site root', () => {
    expect(routeFromUrl('https://explore.burtonmi.gov/')).toBe('');
    expect(routeFromUrl('https://explore.burtonmi.gov')).toBe('');
  });

  it('ignores a different host', () => {
    expect(routeFromUrl('https://evil.example.com/#finances')).toBeNull();
    expect(routeFromUrl('https://burtonmi.gov/#finances')).toBeNull();
  });

  it('ignores an unparseable URL', () => {
    expect(routeFromUrl('not a url')).toBeNull();
  });
});
