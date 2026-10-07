import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import {
  findPrecinct,
  matchAddress,
  normalizeAddress,
  pointInGeometry,
  pointInPolygon,
  suggestAddresses,
  type AddressRow,
  type PrecinctFeature,
} from '../src/lib/guide/precinctFinder';

const square = [
  [0, 0],
  [10, 0],
  [10, 10],
  [0, 10],
  [0, 0],
];
const hole = [
  [4, 4],
  [6, 4],
  [6, 6],
  [4, 6],
  [4, 4],
];

describe('pointInPolygon', () => {
  it('detects a point in a square and outside it', () => {
    expect(pointInPolygon(5, 5, [square])).toBe(true);
    expect(pointInPolygon(11, 5, [square])).toBe(false);
  });
  it('excludes a point inside a hole', () => {
    expect(pointInPolygon(5, 5, [square, hole])).toBe(false);
    expect(pointInPolygon(2, 2, [square, hole])).toBe(true);
  });
  it('handles a MultiPolygon', () => {
    const far = square.map(([x, y]) => [x + 100, y]);
    const g = { type: 'MultiPolygon' as const, coordinates: [[square], [far]] };
    expect(pointInGeometry(105, 5, g)).toBe(true);
    expect(pointInGeometry(2, 2, g)).toBe(true);
    expect(pointInGeometry(50, 5, g)).toBe(false);
  });
});

describe('address normalisation and matching', () => {
  it('matches 4303 S. Center Road to 4303 S Center Rd', () => {
    expect(normalizeAddress('4303 S. Center Road')).toBe(normalizeAddress('4303 S Center Rd'));
    expect(normalizeAddress('  4303   SOUTH  center, rd. ')).toBe('4303 s center rd');
    const rows: AddressRow[] = [{ lat: 1, lng: 2, address: '4303 S Center Rd' }];
    expect(matchAddress('4303 s. center road', rows)?.address).toBe('4303 S Center Rd');
    expect(matchAddress('4304 s center rd', rows)).toBeNull();
  });
});

describe('suggestAddresses', () => {
  const rows: AddressRow[] = [
    '4303 S Center Rd',
    '4304 S Center Rd',
    '4314 S Center Rd',
    '4303 Columbine Ave',
    '4303 Covey Ln',
    '5000 S Center Rd',
    '12 Oak St',
  ].map((address, i) => ({ lat: i, lng: i, address }));

  it('ranks number+street prefix first, then same street by nearness', () => {
    const out = suggestAddresses('430 s center road', rows).map((r) => r.address);
    expect(out[0]).toBe('4303 S Center Rd');
    expect(out[1]).toBe('4304 S Center Rd');
    expect(out).not.toContain('12 Oak St');
    expect(out.length).toBeLessThanOrEqual(5);
  });
  it('falls back to the same street by nearest house number', () => {
    const out = suggestAddresses('4310 S Center Rd', rows).map((r) => r.address);
    expect(out.slice(0, 2)).toEqual(['4314 S Center Rd', '4304 S Center Rd']);
  });
  it('caps at five and returns nothing for empty input', () => {
    const many = Array.from({ length: 20 }, (_, i) => ({
      lat: 0,
      lng: 0,
      address: `${1000 + i} Main St`,
    }));
    expect(suggestAddresses('10 Main St', many)).toHaveLength(5);
    expect(suggestAddresses('   ', many)).toEqual([]);
  });
});

describe('findPrecinct', () => {
  const feats: PrecinctFeature[] = [
    {
      properties: { name: 'City of Burton, Precinct 1', precinct: '1' },
      geometry: { type: 'Polygon', coordinates: [square] },
    },
    {
      properties: { name: 'City of Burton, Precinct 2', precinct: '2' },
      geometry: {
        type: 'Polygon',
        coordinates: [square.map(([x, y]) => [x + 20, y])],
      },
    },
  ];
  it('returns the containing precinct or null', () => {
    expect(findPrecinct(5, 5, feats)?.precinct).toBe('1');
    expect(findPrecinct(5, 25, feats)?.precinct).toBe('2');
    expect(findPrecinct(5, 15, feats)).toBeNull();
  });
});

describe('real data sanity', () => {
  it('resolves 4303 S Center Rd to exactly one precinct', () => {
    const pts = JSON.parse(readFileSync('public/address-points.json', 'utf8')).points as [
      number,
      number,
      string,
    ][];
    const rows = pts.map(([lat, lng, address]) => ({ lat, lng, address }));
    const geo = JSON.parse(readFileSync('public/precincts.geojson', 'utf8'));
    const hit = matchAddress('4303 S Center Rd', rows);
    expect(hit).not.toBeNull();
    const containing = (geo.features as PrecinctFeature[]).filter(
      (f) => f.geometry && pointInGeometry(hit!.lng, hit!.lat, f.geometry),
    );
    expect(containing).toHaveLength(1);
    const p = findPrecinct(hit!.lat, hit!.lng, geo.features);
    console.log('PRECINCT FOR 4303 S Center Rd:', p?.name);
    expect(p).not.toBeNull();
  });
});
