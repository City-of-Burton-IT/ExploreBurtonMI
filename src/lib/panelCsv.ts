// Turn a dashboard panel into downloadable tabular data. Used by both the per-chart
// CSV export in InfoView and the all-datasets Open Data page (#63). Pure (no DOM)
// so the row-building is unit-tested; the browser download lives in csv.ts.

import type { InfoChart, InfoPanel } from './types';
import { formatValue } from './charts/scale';
import { csvRows } from './csv';

export interface CsvTable {
  headers: string[];
  rows: string[][];
}

/** A generic "plain numbers" table for any chart type (same values the chart shows),
 *  or null when the chart has no series/points. */
export function chartToTable(chart: InfoChart): CsvTable | null {
  const unit = chart.unit ?? '';
  if (chart.type === 'bars' || chart.type === 'donut') {
    const series = chart.series ?? [];
    if (!series.length) return null;
    return { headers: ['Category', 'Value'], rows: series.map((s) => [s.label, formatValue(s.value, unit)]) };
  }
  if (chart.type === 'trend') {
    if (chart.lines?.length) {
      const xs: string[] = [];
      for (const ln of chart.lines) for (const p of ln.points) if (!xs.includes(p.x)) xs.push(p.x);
      return {
        headers: ['Period', ...chart.lines.map((l) => l.label)],
        rows: xs.map((x) => [
          x,
          ...chart.lines!.map((l) => {
            const pt = l.points.find((p) => p.x === x);
            return pt ? formatValue(pt.y, unit) : '';
          }),
        ]),
      };
    }
    const points = chart.points ?? [];
    if (!points.length) return null;
    return { headers: ['Period', 'Value'], rows: points.map((p) => [p.x, formatValue(p.y, unit)]) };
  }
  if (chart.type === 'compare') {
    const rows = chart.rows ?? [];
    if (!rows.length) return null;
    const places = rows[0].values.map((v) => v.name);
    return {
      headers: ['Metric', ...places],
      rows: rows.map((r) => [r.label, ...r.values.map((v) => formatValue(v.value, r.unit ?? ''))]),
    };
  }
  return null;
}

/** Every tabular section of a panel (stats, then each chart, then each table), each
 *  titled. The basis for a single combined per-dashboard CSV. */
export function panelSections(panel: InfoPanel): ({ title: string } & CsvTable)[] {
  const sections: ({ title: string } & CsvTable)[] = [];
  if (panel.stats?.length) {
    sections.push({
      title: 'Key statistics',
      headers: ['Metric', 'Value', 'Note'],
      rows: panel.stats.map((s) => [s.label, s.value, s.hint ?? '']),
    });
  }
  for (const c of panel.charts ?? []) {
    const t = chartToTable(c);
    if (t) sections.push({ title: c.title, ...t });
  }
  for (const tb of panel.tables ?? []) {
    sections.push({ title: tb.title, headers: tb.columns, rows: tb.rows.map((r) => r.cells) });
  }
  return sections;
}

/** A single combined CSV for a whole dashboard: each section is a title row, a
 *  header row, its data rows, then a blank separator. Empty when nothing tabular. */
export function panelToCsv(panel: InfoPanel): string {
  const out: string[][] = [];
  for (const s of panelSections(panel)) {
    if (out.length) out.push([]); // blank line between sections
    out.push([s.title], s.headers, ...s.rows);
  }
  return csvRows(out);
}
