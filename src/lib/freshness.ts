// Format an ISO date (YYYY-MM-DD or YYYY-MM) as a resident-facing "Month YYYY"
// freshness label (e.g. "June 2026") for a dashboard's "Data as of ..." line.
// Returns null for empty/invalid input so the caller can simply omit the line.

const FMT = new Intl.DateTimeFormat('en-US', {
  year: 'numeric',
  month: 'long',
  // Parse + format in UTC so a YYYY-MM-DD value never rolls back a day (and a
  // year-end date never rolls into the next year) under the viewer's local tz.
  timeZone: 'UTC',
});

export function formatDataAsOf(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  return FMT.format(d);
}
