import { SITE_BASE } from './hash';

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

/** Canonical, shareable tracking link for a submission. Always the live site
 *  (never the dev-server localhost or the native capacitor:// origin), mirroring
 *  placeShareUrl (#53). The token is base64url so already URL-safe; encode anyway. */
export function trackUrl(token: string, kind: TrackKind): string {
  return `${SITE_BASE}#status?t=${encodeURIComponent(token)}&k=${kind}`;
}

/** Map a raw SharePoint Status to a resident-facing stage; unknown -> "In review". */
export function stageFor(kind: TrackKind, raw: string | null | undefined): string {
  const table = kind === 'report' ? REPORT : LISTING;
  return (raw && table[raw]) || 'In review';
}

export interface StatusResult {
  found: boolean;
  stage?: string;
  updatedAt?: string;
  recap?: string;
  publicNote?: string;
}

/** POST the token as text/plain (no-preflight CORS, same as the intake forms) to the
 *  read flow; return a sanitized, stage-mapped result. Never throws. The fetch arg is
 *  injectable for tests; defaults to global fetch. */
export async function fetchStatus(
  url: string,
  token: string,
  kind: TrackKind,
  fetchImpl: typeof fetch = fetch,
): Promise<StatusResult> {
  try {
    const resp = await fetchImpl(url, {
      method: 'POST',
      headers: { 'Content-Type': 'text/plain;charset=UTF-8' },
      body: JSON.stringify({ token, kind }),
    });
    if (!resp.ok) return { found: false };
    const d = await resp.json();
    if (!d || !d.found) return { found: false };
    return {
      found: true,
      stage: stageFor((d.kind as TrackKind) || kind, d.status),
      updatedAt: d.updatedAt,
      recap: d.recap,
      publicNote: d.publicNote || undefined,
    };
  } catch {
    return { found: false };
  }
}
