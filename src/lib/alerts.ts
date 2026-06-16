// City Alerts -- the data model + pure selection logic behind AlertBanner.svelte.
// Driven by public/alerts.json (committed, city-curated). Display-only public
// content (no resident PII), so it lives outside the map's public-safe gate.

export type AlertLevel = 'emergency' | 'warning' | 'info';

export interface AlertLink {
  text: string;
  href: string;
}

export interface CityAlert {
  /** stable id; the per-alert dismissal is keyed on this (change the id -- e.g.
   *  by appending a new date -- to re-surface a dismissed notice). */
  id: string;
  level: AlertLevel;
  title: string;
  message: string;
  link?: AlertLink;
  /** ISO YYYY-MM-DD: first day the alert is shown */
  start: string;
  /** ISO YYYY-MM-DD: last day the alert is shown (inclusive) */
  end: string;
}

export interface AlertsBundle {
  /** the date the city last edited the file (display only) */
  updated?: string;
  alerts: CityAlert[];
}

// Most-urgent first. emergency (red) > warning (amber) > info (civic blue).
const LEVEL_RANK: Record<AlertLevel, number> = { emergency: 0, warning: 1, info: 2 };

const LEVELS: readonly string[] = ['emergency', 'warning', 'info'];

/** A raw alert as it arrives from either source: the live banner read flow (flat,
 *  with a `linkHref` string) or the committed alerts.json (a `link` object). */
interface RawAlert {
  id: string | number;
  level?: string;
  title?: string;
  message?: string;
  start?: string;
  end?: string;
  /** live-flow shape: a bare href string ('' when none) */
  linkHref?: string;
  /** alerts.json shape: a full link object */
  link?: AlertLink;
}

/**
 * Normalize a raw alert (from either source) into a CityAlert. Coerces id to a
 * string, defaults an unknown level to 'info', and builds the link object from
 * either an existing `link` (alerts.json) or a non-empty `linkHref` (live flow).
 * One shape downstream, regardless of source.
 */
export function normalizeAlert(raw: RawAlert): CityAlert {
  const level = (LEVELS.includes(raw.level ?? '') ? raw.level : 'info') as AlertLevel;
  const link =
    raw.link && raw.link.href
      ? raw.link
      : raw.linkHref
        ? { text: 'More information', href: raw.linkHref }
        : undefined;
  const out: CityAlert = {
    id: String(raw.id),
    level,
    title: raw.title ?? '',
    message: raw.message ?? '',
    start: raw.start ?? '',
    end: raw.end ?? '',
  };
  if (link) out.link = link;
  return out;
}

/**
 * Load city alerts, live-first with an offline fallback: try the read-flow
 * endpoint (config.alerts.url) and, on any failure or non-OK response, fall back
 * to the committed alerts.json. Never throws -> returns [] if both fail. The fetch
 * impl is injectable for tests (pass dataFetch in the app for the native hybrid).
 */
export async function loadAlerts(
  liveUrl: string | undefined,
  fetchImpl: (url: string) => Promise<Response> = fetch,
): Promise<CityAlert[]> {
  const tryFetch = async (url: string): Promise<CityAlert[] | null> => {
    try {
      const r = await fetchImpl(url);
      if (!r.ok) return null;
      const b = (await r.json()) as { alerts?: RawAlert[] } | null;
      return b && Array.isArray(b.alerts) ? b.alerts.map(normalizeAlert) : null;
    } catch {
      return null;
    }
  };
  if (liveUrl) {
    const live = await tryFetch(liveUrl);
    if (live) return live;
  }
  return (await tryFetch('alerts.json')) ?? [];
}

/**
 * The alerts to show right now: active by date (start <= today <= end), not
 * already dismissed on this device, highest level first.
 *
 * `today` and the start/end fields are ISO YYYY-MM-DD strings, for which a
 * lexicographic compare IS a chronological compare -- so no Date parsing is
 * needed (and no timezone surprises). Pass today as the browser's local date.
 */
export function activeAlerts(
  alerts: CityAlert[],
  today: string,
  dismissed: ReadonlySet<string> = new Set(),
): CityAlert[] {
  return alerts
    .filter((a) => a.start <= today && today <= a.end && !dismissed.has(a.id))
    .sort((a, b) => LEVEL_RANK[a.level] - LEVEL_RANK[b.level]);
}
