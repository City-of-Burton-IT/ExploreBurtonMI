import { describe, it, expect } from 'vitest';
import {
  activeClosures,
  closuresGeoJSON,
  closuresSignature,
  localTodayISO,
  type RoadClosure,
} from '../src/lib/closures';

const mk = (over: Partial<RoadClosure> = {}): RoadClosure => ({
  road: 'Maple Rd',
  segment: 'Center Rd to Belsay Rd',
  reason: 'Water main replacement',
  start: '2026-06-10',
  end: '2026-06-20',
  status: 'full',
  ...over,
});

describe('activeClosures', () => {
  it('includes a closure active on the reference day', () => {
    expect(activeClosures([mk()], '2026-06-15')).toHaveLength(1);
  });

  it('includes the exact start and end days (inclusive)', () => {
    expect(activeClosures([mk()], '2026-06-10')).toHaveLength(1);
    expect(activeClosures([mk()], '2026-06-20')).toHaveLength(1);
  });

  it('excludes future and expired closures', () => {
    expect(activeClosures([mk()], '2026-06-09')).toHaveLength(0);
    expect(activeClosures([mk()], '2026-06-21')).toHaveLength(0);
  });

  it('skips closures with missing dates', () => {
    expect(activeClosures([mk({ start: '' })], '2026-06-15')).toHaveLength(0);
    expect(activeClosures([mk({ end: '' })], '2026-06-15')).toHaveLength(0);
  });
});

describe('localTodayISO', () => {
  it('uses the local clock, zero-padded', () => {
    expect(localTodayISO(new Date(2026, 5, 3))).toBe('2026-06-03');
  });
});

describe('closuresSignature', () => {
  it('is order-independent and changes when the set changes', () => {
    const a = mk();
    const b = mk({ road: 'Genesee Rd', start: '2026-06-12', end: '2026-06-14' });
    expect(closuresSignature([a, b])).toBe(closuresSignature([b, a]));
    expect(closuresSignature([a])).not.toBe(closuresSignature([a, b]));
  });
});

describe('closuresGeoJSON', () => {
  it('includes only closures with geometry, coloured by status', () => {
    const withLine = mk({
      geometry: { type: 'LineString', coordinates: [[-83.6, 42.99], [-83.62, 42.99]] },
    });
    const withPoint = mk({
      road: 'Genesee Rd',
      status: 'partial',
      geometry: { type: 'Point', coordinates: [-83.63, 43.0] },
    });
    const noGeom = mk({ road: 'Atherton Rd', geometry: undefined });
    const fc = closuresGeoJSON([withLine, withPoint, noGeom]);
    expect(fc.features).toHaveLength(2);
    const props = fc.features.map((f) => (f as { properties: Record<string, string> }).properties);
    expect(props[0]._color).toBe('#d93025'); // full
    expect(props[1]._color).toBe('#f29900'); // partial
    expect(props[0].road).toBe('Maple Rd');
  });

  it('defaults a missing status to full', () => {
    const fc = closuresGeoJSON([
      mk({ status: undefined, geometry: { type: 'Point', coordinates: [-83.6, 43.0] } }),
    ]);
    const p = (fc.features[0] as { properties: Record<string, string> }).properties;
    expect(p.status).toBe('full');
    expect(p._color).toBe('#d93025');
  });
});
