// "Suggest an edit" submissions (#3): build, validate, and submit a listing
// change request to the M365 intake flow (Power Automate HTTP trigger ->
// SharePoint moderation list). Nothing publishes without IT approval -- the
// SharePoint list is the gate; this module only files the request.
//
// The POST is sent as text/plain so the browser treats it as a CORS "simple
// request" (no OPTIONS preflight -- the flow trigger cannot answer one); the
// flow parses the JSON from the raw body.

export const CHANGE_TYPES = [
  'Fix listing',
  'Permanently closed',
  'Moved',
  'Add my business',
] as const;
export type ChangeType = (typeof CHANGE_TYPES)[number];

export interface SuggestInput {
  changeType: ChangeType | '';
  businessName: string;
  listingId?: string;
  newName?: string;
  newAddress?: string;
  newPhone?: string;
  newWebsite?: string;
  newCategory?: string;
  newHours?: string;
  newCoordinates?: string;
  details?: string;
  contactName: string;
  contactPhoneEmail: string;
  contactRelationship: string;
  /** honeypot -- humans never fill this; bots that do are rejected server-side */
  hp?: string;
}

/** Single-field length cap (SharePoint single-line columns hold 255). */
const FIELD_MAX = 255;
/** Long-text cap (details / hours). */
const LONG_MAX = 2000;

/** Trim every field and drop empty optionals -- the wire payload stays small. */
export function buildPayload(input: SuggestInput): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [k, v] of Object.entries(input)) {
    const t = (v ?? '').toString().trim();
    if (t !== '') out[k] = t;
  }
  // The honeypot is ALWAYS sent (empty) so the server-side check distinguishes
  // "real form" from a scripted POST that omits it entirely.
  out.hp = (input.hp ?? '').toString().trim();
  return out;
}

/**
 * Client-side validation, mirroring (and slightly tightening) the flow's gate.
 * Returns human-readable problems; empty array = submittable.
 */
export function validateSuggestion(input: SuggestInput): string[] {
  const problems: string[] = [];
  const has = (s: string | undefined) => (s ?? '').trim() !== '';

  if (!CHANGE_TYPES.includes(input.changeType as ChangeType))
    problems.push('Pick what you want to do.');
  if (!has(input.businessName)) problems.push('The business name is required.');
  if (!has(input.contactName)) problems.push('Your name is required.');
  if (!has(input.contactPhoneEmail)) problems.push('A phone or email is required so we can confirm.');
  if (!has(input.contactRelationship)) problems.push('Your relationship to the business is required.');
  if ((input.changeType === 'Add my business' || input.changeType === 'Moved') && !has(input.newAddress))
    problems.push('The address is required for this request.');

  for (const [k, v] of Object.entries(input)) {
    const t = (v ?? '').toString().trim();
    const max = k === 'details' || k === 'newHours' ? LONG_MAX : FIELD_MAX;
    if (t.length > max) problems.push(`"${k}" is too long (max ${max} characters).`);
  }
  return problems;
}

export interface SubmitResult {
  ok: boolean;
  /** safe, user-displayable error summary */
  error?: string;
}

/** POST the payload to the intake flow. Never throws. */
export async function submitSuggestion(
  url: string,
  payload: Record<string, string>,
  fetchFn: typeof fetch = fetch,
): Promise<SubmitResult> {
  try {
    const res = await fetchFn(url, {
      method: 'POST',
      headers: { 'Content-Type': 'text/plain' },
      body: JSON.stringify(payload),
    });
    if (res.ok) return { ok: true };
    return {
      ok: false,
      error:
        res.status === 400
          ? 'The request was missing required information.'
          : 'The submission service had a problem. Please try again later.',
    };
  } catch {
    return { ok: false, error: 'Could not reach the submission service. Are you online?' };
  }
}
