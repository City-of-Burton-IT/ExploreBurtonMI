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
