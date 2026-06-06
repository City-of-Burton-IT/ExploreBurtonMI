// Pure, DOM-free layout math for the hand-rolled SVG charts. Kept separate from
// the Svelte components so it can be unit-tested. No rendering, no dependencies.

import type { InfoSeriesItem } from '../types';

/** The civic-blue brand color, shared by every chart. Keep in sync with the
 *  `--civic-blue` CSS token in app.css (SVG fills can't read a CSS var directly). */
export const CIVIC_BLUE = '#2c57a0';

/** Brand-aligned categorical palette (civic spine first, then map category hues). */
export const DEFAULT_PALETTE: string[] = [
  CIVIC_BLUE, // civic blue
  '#4ea735', // civic green
  '#e08a00', // orange
  '#6a1b9a', // purple
  '#00838f', // teal
  '#c2185b', // pink
  '#1565c0', // blue
  '#8e24aa', // violet
];

function colorAt(item: InfoSeriesItem, i: number, palette: string[]): string {
  return item.color ?? palette[i % palette.length];
}

/** Render a numeric value with a unit and thousands separators. A unit beginning
 *  with "$" is a currency prefix (unit "$M" + 12.3 -> "$12.3M"); otherwise it is a
 *  suffix ("%" -> "12.3%"). */
export function formatValue(value: number, unit = ''): string {
  const n = value.toLocaleString('en-US', { maximumFractionDigits: 1 });
  return unit.startsWith('$') ? `$${n}${unit.slice(1)}` : `${n}${unit}`;
}

const nonNeg = (n: number): number => (n > 0 ? n : 0);

export interface DonutSegment {
  label: string;
  value: number;
  color: string;
  pct: number;
  /** dash length (the visible arc) */
  dash: number;
  /** remaining circumference */
  gap: number;
  /** cumulative dash length before this segment (drives stroke-dashoffset) */
  offset: number;
}

export interface DonutLayout {
  total: number;
  circumference: number;
  segments: DonutSegment[];
}

/** Split a circle of the given radius into proportional arc segments. */
export function donutSegments(
  series: InfoSeriesItem[],
  radius: number,
  palette: string[] = DEFAULT_PALETTE,
): DonutLayout {
  const circumference = 2 * Math.PI * radius;
  const total = series.reduce((s, it) => s + nonNeg(it.value), 0);
  if (total <= 0) return { total: 0, circumference, segments: [] };

  const segments: DonutSegment[] = [];
  let offset = 0;
  series.forEach((it, i) => {
    const frac = nonNeg(it.value) / total;
    const dash = frac * circumference;
    segments.push({
      label: it.label,
      value: it.value,
      color: colorAt(it, i, palette),
      pct: frac * 100,
      dash,
      gap: circumference - dash,
      offset,
    });
    offset += dash;
  });
  return { total, circumference, segments };
}

export interface BarRow {
  label: string;
  value: number;
  color: string;
  /** width as a percentage of the largest bar */
  pct: number;
}

/** Scale each bar to a percentage of the largest value. */
export function barRows(
  series: InfoSeriesItem[],
  palette: string[] = DEFAULT_PALETTE,
): BarRow[] {
  const max = series.reduce((m, it) => Math.max(m, nonNeg(it.value)), 0);
  return series.map((it, i) => ({
    label: it.label,
    value: it.value,
    color: colorAt(it, i, palette),
    pct: max > 0 ? (nonNeg(it.value) / max) * 100 : 0,
  }));
}

export interface TrendDot {
  x: number;
  y: number;
  label: string;
  value: number;
}

export interface TrendLayout {
  dots: TrendDot[];
  polyline: string;
  yMin: number;
  yMax: number;
}

/** Map a small series of points into an SVG coordinate box (y inverted: higher
 *  value = higher on screen). `pad` insets all four edges. */
export function trendLayout(
  points: { x: string; y: number }[],
  width: number,
  height: number,
  pad: number,
): TrendLayout {
  if (points.length === 0) return { dots: [], polyline: '', yMin: 0, yMax: 0 };

  const ys = points.map((p) => p.y);
  const yMin = Math.min(...ys);
  const yMax = Math.max(...ys);
  const yspan = yMax - yMin;
  const n = points.length;
  const step = n > 1 ? (width - 2 * pad) / (n - 1) : 0;
  const plotH = height - 2 * pad;

  const dots: TrendDot[] = points.map((p, i) => {
    const x = n > 1 ? pad + i * step : pad;
    const y = yspan > 0 ? height - pad - ((p.y - yMin) / yspan) * plotH : height / 2;
    return { x, y, label: p.x, value: p.y };
  });
  const polyline = dots.map((d) => `${d.x},${d.y}`).join(' ');
  return { dots, polyline, yMin, yMax };
}
