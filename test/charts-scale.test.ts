import { describe, it, expect } from 'vitest';
import {
  donutSegments,
  barRows,
  trendLayout,
  DEFAULT_PALETTE,
} from '../src/lib/charts/scale';

const C = (r: number) => 2 * Math.PI * r;

describe('donutSegments', () => {
  it('splits the circumference proportionally and accumulates offsets', () => {
    const out = donutSegments(
      [
        { label: 'A', value: 3 },
        { label: 'B', value: 1 },
      ],
      50,
    );
    expect(out.total).toBe(4);
    expect(out.segments).toHaveLength(2);
    // percentages
    expect(out.segments[0].pct).toBeCloseTo(75, 5);
    expect(out.segments[1].pct).toBeCloseTo(25, 5);
    // dash lengths sum to the circumference
    const sum = out.segments[0].dash + out.segments[1].dash;
    expect(sum).toBeCloseTo(C(50), 5);
    // first offset 0, second offset = first dash
    expect(out.segments[0].offset).toBe(0);
    expect(out.segments[1].offset).toBeCloseTo(out.segments[0].dash, 5);
    // gap = circumference - dash
    expect(out.segments[0].gap).toBeCloseTo(C(50) - out.segments[0].dash, 5);
  });

  it('assigns palette colors but respects an explicit color', () => {
    const out = donutSegments(
      [
        { label: 'A', value: 1 },
        { label: 'B', value: 1, color: '#abcdef' },
      ],
      10,
    );
    expect(out.segments[0].color).toBe(DEFAULT_PALETTE[0]);
    expect(out.segments[1].color).toBe('#abcdef');
  });

  it('returns no segments when the total is zero or empty', () => {
    expect(donutSegments([], 50).segments).toEqual([]);
    expect(donutSegments([{ label: 'A', value: 0 }], 50).total).toBe(0);
    expect(donutSegments([{ label: 'A', value: 0 }], 50).segments).toEqual([]);
  });
});

describe('barRows', () => {
  it('scales each bar to a percentage of the max', () => {
    const rows = barRows([
      { label: 'A', value: 10 },
      { label: 'B', value: 5 },
      { label: 'C', value: 0 },
    ]);
    expect(rows.map((r) => r.pct)).toEqual([100, 50, 0]);
    expect(rows[0].color).toBe(DEFAULT_PALETTE[0]);
  });

  it('respects an explicit color and handles all-zero safely', () => {
    const rows = barRows([
      { label: 'A', value: 0 },
      { label: 'B', value: 0, color: '#123456' },
    ]);
    expect(rows.every((r) => r.pct === 0)).toBe(true);
    expect(rows[1].color).toBe('#123456');
  });
});

describe('trendLayout', () => {
  it('spaces points evenly and inverts y (higher value = higher on screen)', () => {
    const out = trendLayout(
      [
        { x: '21', y: 10 },
        { x: '22', y: 20 },
        { x: '23', y: 15 },
      ],
      300,
      100,
      10,
    );
    expect(out.yMin).toBe(10);
    expect(out.yMax).toBe(20);
    expect(out.dots.map((d) => Math.round(d.x))).toEqual([10, 150, 290]);
    // min value sits at the bottom (h-pad=90), max at the top (pad=10)
    expect(out.dots[0].y).toBeCloseTo(90, 5); // value 10 (min)
    expect(out.dots[1].y).toBeCloseTo(10, 5); // value 20 (max)
    expect(out.dots[2].y).toBeCloseTo(50, 5); // value 15 (mid)
    expect(out.polyline).toBe('10,90 150,10 290,50');
  });

  it('handles a flat series without dividing by zero', () => {
    const out = trendLayout(
      [
        { x: 'a', y: 5 },
        { x: 'b', y: 5 },
      ],
      100,
      100,
      10,
    );
    // all equal -> place on the mid-line, finite values only
    expect(out.dots.every((d) => Number.isFinite(d.y))).toBe(true);
  });

  it('returns empty layout for no points', () => {
    const out = trendLayout([], 100, 100, 10);
    expect(out.dots).toEqual([]);
    expect(out.polyline).toBe('');
  });
});
