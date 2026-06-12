// Road closures (#32): the city curates public/road-closures.json; the app
// shows only currently-active closures (by date, on the browser's local clock),
// draws those with geometry on the map, and raises a dismissible banner.
// Expired closures auto-hide; future ones stay hidden until they start.
// State highways (I-69 / I-475 / M-54) are NOT ingested -- the banner deep-links
// to MDOT MiDrive, which cannot be fetched client-side (no CORS header).

export interface RoadClosure {
  road: string;
  /** e.g. "Center Rd to Belsay Rd" */
  segment?: string;
  reason?: string;
  /** ISO YYYY-MM-DD, inclusive */
  start: string;
  /** ISO YYYY-MM-DD, inclusive */
  end: string;
  /** full (default) or partial (lane/shoulder) */
  status?: 'full' | 'partial';
  detour?: string;
  /** optional: a closed segment (LineString) or an intersection (Point);
   *  closures without geometry appear in the banner but not on the map */
  geometry?:
    | { type: 'LineString'; coordinates: [number, number][] }
    | { type: 'Point'; coordinates: [number, number] };
}

export interface RoadClosuresFile {
  updated?: string;
  closures: RoadClosure[];
}

export const MDOT_MIDRIVE_URL = 'https://mdotjboss.state.mi.us/MiDrive/map';

/** Map colours by closure status -- fixed values readable on the aerial basemap. */
export const CLOSURE_COLORS: Record<string, string> = {
  full: '#d93025',
  partial: '#f29900',
};

/** Today as local-clock ISO YYYY-MM-DD (NOT toISOString, which is UTC and can
 *  be a day off in Michigan evenings). */
export function localTodayISO(now: Date = new Date()): string {
  const m = String(now.getMonth() + 1).padStart(2, '0');
  const d = String(now.getDate()).padStart(2, '0');
  return `${now.getFullYear()}-${m}-${d}`;
}

/** The closures active on `today` (inclusive boundaries; ISO string compare). */
export function activeClosures(closures: RoadClosure[], today: string): RoadClosure[] {
  return closures.filter((c) => c.start && c.end && c.start <= today && today <= c.end);
}

/** Stable signature of the active set -- the banner's dismissal is keyed to it,
 *  so the banner returns whenever the set of active closures changes. */
export function closuresSignature(active: RoadClosure[]): string {
  return active
    .map((c) => `${c.road}|${c.start}|${c.end}|${c.status ?? 'full'}`)
    .sort()
    .join(';');
}

/** GeoJSON FeatureCollection of the active closures that carry geometry. */
export function closuresGeoJSON(active: RoadClosure[]): {
  type: 'FeatureCollection';
  features: object[];
} {
  const features = active
    .filter((c) => c.geometry)
    .map((c) => ({
      type: 'Feature',
      geometry: c.geometry,
      properties: {
        road: c.road,
        segment: c.segment ?? '',
        reason: c.reason ?? '',
        start: c.start,
        end: c.end,
        status: c.status ?? 'full',
        detour: c.detour ?? '',
        _color: CLOSURE_COLORS[c.status ?? 'full'] ?? CLOSURE_COLORS.full,
      },
    }));
  return { type: 'FeatureCollection', features };
}
