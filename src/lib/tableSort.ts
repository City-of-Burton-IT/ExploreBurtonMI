// Client-side sorting for InfoTable. A column is sorted numerically when most of
// its cells parse as numbers (so "3,841", "$1,234", "54%", "918 ac", "15,000/day"
// sort by value, not lexically); otherwise it sorts as text. Pure + testable.

/** Parse a table cell to a number, tolerating $, commas, %, and a trailing unit
 *  ("918 ac", "15,000/day"). Returns null when the cell isn't numeric. */
export function numericValue(s: string): number | null {
  const t = s.trim();
  if (!/^[-+]?\$?[\d,]+(\.\d+)?\s*(%|[a-z/]+)?$/i.test(t)) return null;
  const m = t.replace(/[$,]/g, '').match(/-?\d+(\.\d+)?/);
  return m ? parseFloat(m[0]) : null;
}

/** True when a column should sort numerically (>= 60% of its non-empty cells parse
 *  as numbers). */
export function isNumericColumn(rows: { cells: string[] }[], col: number): boolean {
  let nonEmpty = 0;
  let numeric = 0;
  for (const r of rows) {
    const c = (r.cells[col] ?? '').trim();
    if (!c) continue;
    nonEmpty++;
    if (numericValue(c) !== null) numeric++;
  }
  return numeric > 0 && numeric >= nonEmpty * 0.6;
}

/** Return a new array of rows sorted by `col`. Numeric columns sort by value with
 *  non-numeric cells last; text columns sort with localeCompare. Stable. */
export function sortRows<T extends { cells: string[] }>(
  rows: T[],
  col: number,
  dir: 'asc' | 'desc',
): T[] {
  const numeric = isNumericColumn(rows, col);
  const sign = dir === 'desc' ? -1 : 1;
  return rows
    .map((r, i) => ({ r, i }))
    .sort((a, b) => {
      const ca = (a.r.cells[col] ?? '').trim();
      const cb = (b.r.cells[col] ?? '').trim();
      if (numeric) {
        const na = numericValue(ca);
        const nb = numericValue(cb);
        if (na === null && nb === null) return a.i - b.i;
        if (na === null) return 1; // non-numeric cells last, regardless of dir
        if (nb === null) return -1;
        if (na !== nb) return sign * (na - nb);
        return a.i - b.i;
      }
      const cmp = ca.localeCompare(cb);
      return cmp !== 0 ? sign * cmp : a.i - b.i;
    })
    .map((k) => k.r);
}
