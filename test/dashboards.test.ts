import { describe, it, expect } from 'vitest';
import {
  DASHBOARDS,
  isDashboard,
  adjacentDashboards,
  viewFromHash,
  guideSectionFromHash,
} from '../src/lib/dashboards';

describe('viewFromHash', () => {
  it('maps a dashboard hash to its view', () => {
    expect(viewFromHash('#finances')).toBe('finances');
    expect(viewFromHash('#demographics')).toBe('demographics');
  });

  it('maps guide, opendata, and status hashes', () => {
    expect(viewFromHash('#guide')).toBe('guide');
    expect(viewFromHash('#opendata')).toBe('opendata');
    expect(viewFromHash('#status')).toBe('status');
  });

  it('splits on a trailing sub-path (#guide/trash)', () => {
    expect(viewFromHash('#guide/trash')).toBe('guide');
  });

  it('splits on a query suffix (#status?t=...)', () => {
    expect(viewFromHash('#status?t=abc123')).toBe('status');
  });

  it('falls back to "map" for unknown or empty hashes', () => {
    expect(viewFromHash('#nonsense')).toBe('map');
    expect(viewFromHash('#map/place/abc-123')).toBe('map');
    expect(viewFromHash('')).toBe('map');
    expect(viewFromHash('#')).toBe('map');
  });
});

describe('guideSectionFromHash', () => {
  it('extracts the section id from a #guide/<id> hash', () => {
    expect(guideSectionFromHash('#guide/trash')).toBe('trash');
  });

  it('returns null for a bare #guide hash (no section)', () => {
    expect(guideSectionFromHash('#guide')).toBeNull();
  });

  it('returns null for non-guide hashes', () => {
    expect(guideSectionFromHash('#finances')).toBeNull();
    expect(guideSectionFromHash('#map/place/abc-123')).toBeNull();
    expect(guideSectionFromHash('')).toBeNull();
  });
});

describe('isDashboard', () => {
  it('is true for every registered dashboard id', () => {
    for (const d of DASHBOARDS) expect(isDashboard(d.id)).toBe(true);
  });

  it('is false for non-dashboard views', () => {
    expect(isDashboard('map')).toBe(false);
    expect(isDashboard('guide')).toBe(false);
    expect(isDashboard('opendata')).toBe(false);
    expect(isDashboard('status')).toBe(false);
  });
});

describe('adjacentDashboards', () => {
  it('has no prev for the first dashboard', () => {
    const first = DASHBOARDS[0];
    const { prev, next } = adjacentDashboards(first.id);
    expect(prev).toBeNull();
    expect(next).toEqual(DASHBOARDS[1]);
  });

  it('has no next for the last dashboard', () => {
    const last = DASHBOARDS[DASHBOARDS.length - 1];
    const { prev, next } = adjacentDashboards(last.id);
    expect(next).toBeNull();
    expect(prev).toEqual(DASHBOARDS[DASHBOARDS.length - 2]);
  });

  it('returns the neighbors on either side for a middle dashboard', () => {
    const i = Math.floor(DASHBOARDS.length / 2);
    const { prev, next } = adjacentDashboards(DASHBOARDS[i].id);
    expect(prev).toEqual(DASHBOARDS[i - 1]);
    expect(next).toEqual(DASHBOARDS[i + 1]);
  });

  it('returns { null, null } for an id not in the registry', () => {
    expect(adjacentDashboards('map')).toEqual({ prev: null, next: null });
    expect(adjacentDashboards('guide')).toEqual({ prev: null, next: null });
  });
});
