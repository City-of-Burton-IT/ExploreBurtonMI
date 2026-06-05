// Pure helper: pick the next upcoming meeting. ISO date strings (YYYY-MM-DD)
// compare correctly lexicographically, so no Date parsing is needed.

/** Return the earliest meeting date on or after `refISO`, or null if all are past. */
export function nextMeetingDate(
  meetings: { date: string }[],
  refISO: string,
): string | null {
  let best: string | null = null;
  for (const m of meetings) {
    if (m.date >= refISO && (best === null || m.date < best)) best = m.date;
  }
  return best;
}
