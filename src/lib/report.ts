// "Report an issue" submissions (#14): a resident drops a pin, optionally adds
// a photo + notes, and the report lands in the private DPW triage queue (it is
// never published). Same intake mechanics as suggest.ts (#3): text/plain POST
// to a Power Automate HTTP trigger -- see that file for the CORS rationale.

import { submitSuggestion, type SubmitResult } from './suggest';

// NOTE: three places must stay in sync when this list changes (#67): this
// whitelist, the flow's Validate_and_route createArray(...), and the Category
// choice column on the SharePoint list.
export const REPORT_CATEGORIES = [
  'Pothole',
  'Blight',
  'Sign',
  'Drainage',
  'Streetlight',
  'Other',
] as const;
export type ReportCategory = (typeof REPORT_CATEGORIES)[number];

/** Mirror of the flow's accept box (and roughly the map's maxBounds). */
export const CITY_BOUNDS = { latMin: 42.85, latMax: 43.15, lngMin: -83.85, lngMax: -83.4 };

/** ~2 MB of base64 -- the flow rejects anything bigger. */
export const PHOTO_BASE64_MAX = 2_800_000;

export interface ReportInput {
  category: ReportCategory | '';
  lat: number | null;
  lng: number | null;
  description?: string;
  /** raw base64 (no data: prefix); produced by the photo resizer */
  photoBase64?: string;
  photoName?: string;
  contactName?: string;
  contactInfo?: string;
  /** honeypot -- humans never fill this */
  hp?: string;
}

export function inCity(lat: number, lng: number): boolean {
  return (
    lat >= CITY_BOUNDS.latMin &&
    lat <= CITY_BOUNDS.latMax &&
    lng >= CITY_BOUNDS.lngMin &&
    lng <= CITY_BOUNDS.lngMax
  );
}

/** Client-side validation, mirroring the flow's gate. Empty array = submittable. */
export function validateReport(input: ReportInput): string[] {
  const problems: string[] = [];
  if (!REPORT_CATEGORIES.includes(input.category as ReportCategory))
    problems.push('Pick what kind of issue this is.');
  if (input.lat == null || input.lng == null) {
    problems.push('Tap the map to mark where the issue is.');
  } else if (!inCity(input.lat, input.lng)) {
    problems.push('The pin is outside the City of Burton -- this form only reaches Burton DPW.');
  }
  if ((input.description ?? '').length > 2000)
    problems.push('The description is too long (max 2000 characters).');
  if ((input.photoBase64 ?? '').length > PHOTO_BASE64_MAX)
    problems.push('The photo is too large even after resizing -- try a different photo.');
  for (const k of ['contactName', 'contactInfo'] as const) {
    if ((input[k] ?? '').length > 255) problems.push(`"${k}" is too long (max 255 characters).`);
  }
  return problems;
}

/** Build the wire payload: trim, drop empties, coords as strings, honeypot always present. */
export function buildReportPayload(input: ReportInput): Record<string, string> {
  const out: Record<string, string> = {
    category: (input.category || '').trim(),
    lat: input.lat == null ? '' : String(input.lat),
    lng: input.lng == null ? '' : String(input.lng),
    hp: (input.hp ?? '').trim(),
  };
  for (const k of ['description', 'photoBase64', 'photoName', 'contactName', 'contactInfo'] as const) {
    const t = (input[k] ?? '').trim();
    if (t !== '') out[k] = t;
  }
  return out;
}

/** POST the report to the intake flow. Never throws. */
export function submitReport(
  url: string,
  payload: Record<string, string>,
  fetchFn: typeof fetch = fetch,
): Promise<SubmitResult> {
  return submitSuggestion(url, payload, fetchFn);
}
