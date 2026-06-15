export type TrackKind = 'report' | 'listing';

/** 128-bit URL-safe opaque token (16 random bytes, base64url). */
export function newToken(): string {
  const b = new Uint8Array(16);
  crypto.getRandomValues(b);
  return btoa(String.fromCharCode(...b))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
}

const REPORT: Record<string, string> = {
  New: 'Received',
  'In progress': 'In progress',
  Closed: 'Resolved',
};
const LISTING: Record<string, string> = {
  New: 'Received',
  Approved: 'Approved & published',
  Applied: 'Approved & published',
  Rejected: 'Not accepted',
  'Needs-info': 'Needs more info',
};

/** Map a raw SharePoint Status to a resident-facing stage; unknown -> "In review". */
export function stageFor(kind: TrackKind, raw: string | null | undefined): string {
  const table = kind === 'report' ? REPORT : LISTING;
  return (raw && table[raw]) || 'In review';
}
