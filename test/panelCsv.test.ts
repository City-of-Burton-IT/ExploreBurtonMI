import { describe, it, expect } from 'vitest';
import { chartToTable, panelSections, panelToCsv } from '../src/lib/panelCsv';
import type { InfoChart, InfoPanel } from '../src/lib/types';

const bars: InfoChart = {
  type: 'bars',
  title: 'Calls by station',
  unit: '',
  series: [
    { label: 'Station 1', value: 325 },
    { label: 'Station 2', value: 335 },
  ],
};

const trend: InfoChart = {
  type: 'trend',
  title: 'Calls by year',
  unit: '',
  points: [
    { x: '2014', y: 513 },
    { x: '2015', y: 600 },
  ],
};

const compare: InfoChart = {
  type: 'compare',
  title: 'Condition vs county',
  rows: [{ label: 'Good', unit: '%', values: [{ name: 'Burton', value: 13 }, { name: 'County', value: 10 }] }],
};

describe('chartToTable', () => {
  it('builds Category/Value rows for bars + donut', () => {
    const t = chartToTable(bars)!;
    expect(t.headers).toEqual(['Category', 'Value']);
    expect(t.rows).toEqual([['Station 1', '325'], ['Station 2', '335']]);
  });

  it('builds Period/Value rows for a single-series trend', () => {
    const t = chartToTable(trend)!;
    expect(t.headers).toEqual(['Period', 'Value']);
    expect(t.rows[0]).toEqual(['2014', '513']);
  });

  it('builds Metric/place columns for a compare chart', () => {
    const t = chartToTable(compare)!;
    expect(t.headers).toEqual(['Metric', 'Burton', 'County']);
    expect(t.rows[0]).toEqual(['Good', '13%', '10%']);
  });

  it('returns null when a chart has no data', () => {
    expect(chartToTable({ type: 'bars', title: 'empty', series: [] })).toBeNull();
  });
});

const panel: InfoPanel = {
  title: 'Burton Fire & Rescue',
  source: 'Burton Fire Dept annual stats',
  lastUpdated: '2025-12',
  stats: [{ label: 'Total responses', value: '758', hint: '2025' }],
  charts: [bars, trend],
  tables: [{ title: 'Per station', columns: ['Station', 'Calls'], rows: [{ cells: ['1', '325'] }] }],
};

describe('panelSections / panelToCsv', () => {
  it('emits a section for stats, each chart, and each table', () => {
    const sections = panelSections(panel);
    expect(sections.map((s) => s.title)).toEqual([
      'Key statistics',
      'Calls by station',
      'Calls by year',
      'Per station',
    ]);
  });

  it('combines everything into one CSV with the section titles + a blank separator', () => {
    const csv = panelToCsv(panel);
    expect(csv).toContain('Key statistics');
    expect(csv).toContain('Total responses,758,2025');
    expect(csv).toContain('Calls by station');
    expect(csv).toContain('Per station');
    expect(csv).toContain('\r\n\r\n'); // blank line between sections
  });

  it('is empty for a panel with no tabular data', () => {
    expect(panelToCsv({ title: 'x', stats: [], charts: [] })).toBe('');
  });
});
