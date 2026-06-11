// Pure, DOM-free layout math for the hand-rolled SVG charts. Kept separate from
// the Svelte components so it can be unit-tested. No rendering, no dependencies.

import type { InfoSeriesItem } from '../types';

/** The civic-blue brand color, shared by every chart. Keep in sync with the
 *  `--civic-blue` CSS token in app.css (SVG fills can't read a CSS var directly). */
export const CIVIC_BLUE = '#2c57a0';

/** Brand-aligned categorical palette, ORDERED for colour-vision-deficiency (CVD)
 *  legibility: the brand blue leads, then orange (blue<->orange is the most
 *  CVD-robust pairing), then the brand green; neighbours also differ in LIGHTNESS,
 *  which survives CVD. The two near-duplicate hues (a second blue, a second
 *  purple) are LAST, so they're only reached by 7-8 category charts. Charts also
 *  print the value beside every bar/slice and offer a data table, so colour is
 *  never the sole signal. Verify visually with Chrome DevTools > Rendering >
 *  Emulate vision deficiencies (deuteranopia / protanopia / tritanopia). */
export const DEFAULT_PALETTE: string[] = [
  CIVIC_BLUE, // 1 civic blue   (dark cool, brand)
  '#e08a00', // 2 orange       (warm) -- blue<->orange is the most CVD-safe pair
  '#4ea735', // 3 civic green  (brand)
  '#6a1b9a', // 4 purple       (dark)
  '#00838f', // 5 teal
  '#c2185b', // 6 pink/magenta (warm)
  '#1565c0', // 7 blue         (near civic blue -- last-resort, 7+ categories)
  '#8e24aa', // 8 violet       (near purple -- last-resort)
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

export interface MultiTrendLine {
  label: string;
  color: string;
  polyline: string;
  dots: TrendDot[];
}

export interface MultiTrendLayout {
  lines: MultiTrendLine[];
  /** shared x-axis labels (union of all series' x values, in first-seen order) */
  xLabels: string[];
  yMin: number;
  yMax: number;
}

/** Lay out several trend series in one box with a SHARED x and y scale, so the
 *  lines are directly comparable. x positions come from the union of x labels
 *  (evenly spaced by index); y spans the min/max across every line. */
export function multiTrendLayout(
  lines: { label: string; points: { x: string; y: number }[]; color?: string }[],
  width: number,
  height: number,
  pad: number,
  palette: string[] = DEFAULT_PALETTE,
): MultiTrendLayout {
  const xLabels: string[] = [];
  for (const ln of lines) {
    for (const p of ln.points) {
      if (!xLabels.includes(p.x)) xLabels.push(p.x);
    }
  }
  const allY = lines.flatMap((ln) => ln.points.map((p) => p.y));
  if (xLabels.length === 0 || allY.length === 0) {
    return { lines: [], xLabels: [], yMin: 0, yMax: 0 };
  }

  const yMin = Math.min(...allY);
  const yMax = Math.max(...allY);
  const yspan = yMax - yMin;
  const n = xLabels.length;
  const step = n > 1 ? (width - 2 * pad) / (n - 1) : 0;
  const plotH = height - 2 * pad;

  const xAt = (label: string): number => {
    const i = xLabels.indexOf(label);
    return n > 1 ? pad + i * step : pad;
  };
  const yAt = (v: number): number =>
    yspan > 0 ? height - pad - ((v - yMin) / yspan) * plotH : height / 2;

  const out: MultiTrendLine[] = lines.map((ln, li) => {
    const dots: TrendDot[] = ln.points.map((p) => ({
      x: xAt(p.x),
      y: yAt(p.y),
      label: p.x,
      value: p.y,
    }));
    return {
      label: ln.label,
      color: ln.color ?? palette[li % palette.length],
      polyline: dots.map((d) => `${d.x},${d.y}`).join(' '),
      dots,
    };
  });

  return { lines: out, xLabels, yMin, yMax };
}
