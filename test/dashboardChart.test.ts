import { render } from 'svelte/server';
import { describe, expect, it } from 'vitest';
import DashboardChart from '../src/lib/dashboard/DashboardChart.svelte';
import type { InfoChart } from '../src/lib/dashboard/infoPanel';

const examples: { type: InfoChart['type']; chart: InfoChart; chartMarker: string }[] = [
  {
    type: 'donut',
    chart: { type: 'donut', title: 'Donut title', unit: '%', series: [{ label: 'Yes', value: 60 }] },
    chartMarker: 'aria-label="Proportional breakdown"',
  },
  {
    type: 'bars',
    chart: { type: 'bars', title: 'Bars title', series: [{ label: 'Total', value: 10 }] },
    chartMarker: 'class="bars',
  },
  {
    type: 'trend',
    chart: { type: 'trend', title: 'Trend title', points: [{ x: '2026', y: 10 }] },
    chartMarker: 'aria-label="Trend over time"',
  },
  {
    type: 'compare',
    chart: {
      type: 'compare',
      title: 'Compare title',
      rows: [{ label: 'Rate', unit: '%', values: [{ name: 'Burton', value: 10 }] }],
    },
    chartMarker: 'class="compare',
  },
];

describe('DashboardChart', () => {
  it.each(examples)('renders the $type chart and its matching accessible data table', ({ chart, chartMarker }) => {
    const { body } = render(DashboardChart, { props: { chart } });

    expect(body).toMatch(new RegExp(`<figcaption[^>]*>${chart.title}</figcaption>`));
    expect(body).toContain(chartMarker);
    expect(body).toContain('View data table');
    expect(body).toMatch(new RegExp(`<caption class="sr-only[^"]*">${chart.title}</caption>`));
    expect(body).toContain('Download CSV');
  });
});
