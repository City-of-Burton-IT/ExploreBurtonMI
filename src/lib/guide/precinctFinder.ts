// "Find my voting precinct": match a typed Burton street address against the
// committed address table, then test which precinct polygon contains the point.
// Pure functions only; the component owns loading and UI. Runs on-device.

export interface AddressRow {
  lat: number;
  lng: number;
  address: string;
}

type Ring = number[][];
export interface PrecinctGeometry {
  type: 'Polygon' | 'MultiPolygon';
  coordinates: number[][][] | number[][][][];
}
export interface PrecinctFeature {
  properties?: { name?: string; precinct?: string } | null;
  geometry: PrecinctGeometry | null;
}
export interface PrecinctHit {
  name: string;
  precinct: string;
}

/** Ray casting on one ring of [lng, lat] pairs. */
export function pointInRing(lng: number, lat: number, ring: Ring): boolean {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const xi = ring[i][0];
    const yi = ring[i][1];
    const xj = ring[j][0];
    const yj = ring[j][1];
    if (yi > lat !== yj > lat && lng < ((xj - xi) * (lat - yi)) / (yj - yi) + xi) {
      inside = !inside;
    }
  }
  return inside;
}

/** Polygon = [outer, ...holes]. Inside the outer ring and in no hole. */
export function pointInPolygon(lng: number, lat: number, rings: Ring[]): boolean {
  if (rings.length === 0 || !pointInRing(lng, lat, rings[0])) return false;
  for (let k = 1; k < rings.length; k++) {
    if (pointInRing(lng, lat, rings[k])) return false;
  }
  return true;
}

export function pointInGeometry(lng: number, lat: number, geom: PrecinctGeometry): boolean {
  if (geom.type === 'Polygon') return pointInPolygon(lng, lat, geom.coordinates as Ring[]);
  if (geom.type === 'MultiPolygon') {
    return (geom.coordinates as Ring[][]).some((poly) => pointInPolygon(lng, lat, poly));
  }
  return false;
}

/** The precinct containing (lat, lng), or null when outside every polygon. */
export function findPrecinct(
  lat: number,
  lng: number,
  features: readonly PrecinctFeature[],
): PrecinctHit | null {
  for (const f of features) {
    if (!f.geometry || !pointInGeometry(lng, lat, f.geometry)) continue;
    const precinct = f.properties?.precinct ?? '';
    const name = f.properties?.name ?? (precinct ? `Precinct ${precinct}` : 'Precinct');
    return { name, precinct };
  }
  return null;
}

// Every spelling is folded to the short form, so abbreviations match both ways.
const ABBREV: Record<string, string> = {
  road: 'rd',
  street: 'st',
  drive: 'dr',
  avenue: 'ave',
  court: 'ct',
  lane: 'ln',
  north: 'n',
  south: 's',
  east: 'e',
  west: 'w',
};

/** Lower-case, drop punctuation and extra spaces, fold abbreviations. */
export function normalizeAddress(input: string): string {
  return input
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, ' ')
    .split(/\s+/)
    .filter((t) => t !== '')
    .map((t) => ABBREV[t] ?? t)
    .join(' ');
}

function splitAddress(norm: string): { num: string; street: string } {
  const m = /^(\d+)\s*(.*)$/.exec(norm);
  return m ? { num: m[1], street: m[2] } : { num: '', street: norm };
}

/** Exact match on the normalised address, or null. */
export function matchAddress(input: string, rows: readonly AddressRow[]): AddressRow | null {
  const q = normalizeAddress(input);
  if (q === '') return null;
  for (const r of rows) if (normalizeAddress(r.address) === q) return r;
  return null;
}

/** Up to `limit` closest addresses: same number + street prefix first, then
 *  the same street by nearest house number, then street-prefix only. */
export function suggestAddresses(
  input: string,
  rows: readonly AddressRow[],
  limit = 5,
): AddressRow[] {
  const q = splitAddress(normalizeAddress(input));
  if (q.num === '' && q.street === '') return [];
  const qn = q.num === '' ? NaN : Number(q.num);
  const scored: { row: AddressRow; tier: number; dist: number }[] = [];
  const seen = new Set<string>();
  for (const row of rows) {
    const a = splitAddress(normalizeAddress(row.address));
    const key = `${a.num} ${a.street}`;
    if (seen.has(key)) continue;
    const streetPrefix = q.street === '' || a.street.startsWith(q.street);
    const sameStreet = a.street === q.street;
    const numPrefix = q.num !== '' && a.num.startsWith(q.num);
    const dist = Number.isNaN(qn) ? 0 : Math.abs(Number(a.num) - qn);
    let tier = -1;
    if (numPrefix && streetPrefix) tier = 0;
    else if (sameStreet && q.num !== '') tier = 1;
    else if (streetPrefix && q.street !== '') tier = 2;
    if (tier < 0) continue;
    seen.add(key);
    scored.push({ row, tier, dist });
  }
  scored.sort(
    (x, y) => x.tier - y.tier || x.dist - y.dist || x.row.address.localeCompare(y.row.address),
  );
  return scored.slice(0, limit).map((s) => s.row);
}
