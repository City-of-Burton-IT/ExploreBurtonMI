import { describe, it, expect } from 'vitest';
import { seriesDelta } from '../src/lib/charts/scale';

describe('seriesDelta', () => {
  it('computes a signed percent change from first to last point', () => {
    expect(seriesDelta([{ x: '2021', y: 100 }, { x: '2025', y: 115 }])).toEqual({
      pctText: '+15%',
      direction: 'up',
      fromLabel: '2021',
      toLabel: '2025',
    });
  });

  it('reports a decrease', () => {
    const d = seriesDelta([{ x: 'a', y: 200 }, { x: 'b', y: 184 }]);
    expect(d?.pctText).toBe('-8%');
    expect(d?.direction).toBe('down');
  });

  it('reports flat when unchanged', () => {
    const d = seriesDelta([{ x: 'a', y: 50 }, { x: 'b', y: 50 }]);
    expect(d?.pctText).toBe('0%');
    expect(d?.direction).toBe('flat');
  });

  it('uses only the first and last of a longer series', () => {
    const d = seriesDelta([
      { x: '14', y: 513 },
      { x: '20', y: 900 },
      { x: '25', y: 758 },
    ]);
    expect(d?.fromLabel).toBe('14');
    expect(d?.toLabel).toBe('25');
    expect(d?.pctText).toBe('+48%');
  });

  it('returns null for too-few points or a zero baseline', () => {
    expect(seriesDelta([{ x: 'a', y: 5 }])).toBeNull();
    expect(seriesDelta([])).toBeNull();
    expect(seriesDelta([{ x: 'a', y: 0 }, { x: 'b', y: 10 }])).toBeNull();
  });
});
