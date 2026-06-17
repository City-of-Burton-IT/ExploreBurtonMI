import { describe, it, expect, vi, afterEach } from 'vitest';
import {
  haversineMeters,
  parseAddressPoints,
  nearestAddress,
  loadAddressPoints,
  _resetAddressPointCache,
  type AddressPoint,
} from '../src/lib/reverseGeocode';

describe('haversineMeters', () => {
  it('is zero for identical points', () => {
    expect(haversineMeters(43.002, -83.632, 43.002, -83.632)).toBeCloseTo(0, 5);
  });

  it('measures ~111 m for 0.001 deg of latitude', () => {
    // 1 deg latitude ~= 111.19 km, so 0.001 deg ~= 111.19 m.
    const d = haversineMeters(43.0, -83.632, 43.001, -83.632);
    expect(d).toBeGreaterThan(108);
    expect(d).toBeLessThan(114);
  });
});

describe('parseAddressPoints', () => {
  it('parses the compact {points:[[lat,lng,address]]} table', () => {
    const json = {
      updated: '2026-06-17',
      points: [
        [43.0, -83.63, '3025 S Center Rd'],
        [43.01, -83.64, '100 Maple Ave'],
      ],
    };
    expect(parseAddressPoints(json)).toEqual([
      { lat: 43.0, lng: -83.63, address: '3025 S Center Rd' },
      { lat: 43.01, lng: -83.64, address: '100 Maple Ave' },
    ]);
  });

  it('skips malformed rows (bad coords or empty address) but keeps valid ones', () => {
    const json = {
      points: [
        [43.0, -83.63, '3025 S Center Rd'],
        [43.0, -83.63, ''], // empty address
        ['x', -83.63, '1 Bad Ln'], // non-numeric lat
        [43.0, null, '2 Bad Ln'], // null lng
        [43.02, -83.62, '500 Belsay Rd'],
      ],
    };
    expect(parseAddressPoints(json)).toEqual([
      { lat: 43.0, lng: -83.63, address: '3025 S Center Rd' },
      { lat: 43.02, lng: -83.62, address: '500 Belsay Rd' },
    ]);
  });

  it('returns [] for missing/empty/garbage input', () => {
    expect(parseAddressPoints(null)).toEqual([]);
    expect(parseAddressPoints({})).toEqual([]);
    expect(parseAddressPoints({ points: [] })).toEqual([]);
    expect(parseAddressPoints({ points: 'nope' })).toEqual([]);
  });
});

describe('nearestAddress', () => {
  const points: AddressPoint[] = [
    { lat: 43.0, lng: -83.63, address: '3025 S Center Rd' },
    { lat: 43.01, lng: -83.64, address: '100 Maple Ave' },
    { lat: 43.05, lng: -83.7, address: '999 Far Away Dr' },
  ];

  it('returns the closest point to the dropped pin', () => {
    const r = nearestAddress(43.0001, -83.6301, points);
    expect(r?.address).toBe('3025 S Center Rd');
    expect(r?.distanceM).toBeGreaterThan(0);
    expect(r?.distanceM).toBeLessThan(50);
  });

  it('returns null for an empty point list', () => {
    expect(nearestAddress(43.0, -83.63, [])).toBeNull();
  });

  it('returns null when the closest point is beyond maxDistanceM', () => {
    // Pin ~1.5 km from the nearest point, default cap should reject it.
    expect(nearestAddress(43.02, -83.61, points)).toBeNull();
  });

  it('honors a custom maxDistanceM', () => {
    // Same far pin, but a generous cap should now return the nearest. At 43N
    // longitude is compressed, so 100 Maple Ave is marginally closer than
    // 3025 S Center Rd despite the raw degree deltas looking similar.
    const r = nearestAddress(43.02, -83.61, points, 5000);
    expect(r?.address).toBe('100 Maple Ave');
  });
});

describe('loadAddressPoints', () => {
  afterEach(() => {
    _resetAddressPointCache();
    vi.unstubAllGlobals();
  });

  it('fetches the source once and parses it, caching the result', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ points: [[43.0, -83.63, '3025 S Center Rd']] }),
    });
    vi.stubGlobal('fetch', fetchMock);

    const first = await loadAddressPoints('address-points.json');
    const second = await loadAddressPoints('address-points.json');

    expect(first).toEqual([{ lat: 43.0, lng: -83.63, address: '3025 S Center Rd' }]);
    expect(second).toBe(first); // same cached promise result
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('resolves to [] on a network failure (offline) without throwing', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')));
    await expect(loadAddressPoints('address-points.json')).resolves.toEqual([]);
  });

  it('resolves to [] on a non-OK response (missing file)', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 404 }));
    await expect(loadAddressPoints('address-points.json')).resolves.toEqual([]);
  });
});
