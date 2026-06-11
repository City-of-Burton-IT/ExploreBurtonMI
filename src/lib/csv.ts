// Shared CSV helpers for the dashboards: charts and per-item tables both export
// their displayed values as a downloadable CSV. Pure serialization is split from
// the browser download so it can be unit-tested.

/** Slugify a title into a safe filename stem (e.g. "Largest districts (acres)"
 *  -> "largest-districts-acres"); falls back to "data" if nothing remains. */
export function csvSlug(s: string): string {
  return s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') || 'data';
}

/** Serialize a header row + data rows to CSV text (CRLF line endings). Fields
 *  containing a comma, quote, or newline are quoted and embedded quotes doubled. */
export function toCsv(headers: string[], rows: string[][]): string {
  const esc = (s: string) => (/[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s);
  return [headers, ...rows].map((r) => r.map(esc).join(',')).join('\r\n');
}

/** Trigger a browser download of the given table as `<filename>.csv`. */
export function downloadCsv(filename: string, headers: string[], rows: string[][]): void {
  const csv = toCsv(headers, rows);
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
  const a = document.createElement('a');
  a.href = url;
  a.download = filename.endsWith('.csv') ? filename : `${filename}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
