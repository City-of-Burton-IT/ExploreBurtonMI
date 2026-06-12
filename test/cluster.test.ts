import { describe, it, expect } from 'vitest';
import { clusterSummary } from '../src/lib/cluster';

describe('clusterSummary', () => {
  it('dedupes, sorts alphabetically, and caps at max', () => {
    const { shown, more } = clusterSummary(['Cafe B', 'Shop A', 'Cafe B', 'Zed', 'Mid'], 3);
    expect(shown).toEqual(['Cafe B', 'Mid', 'Shop A']);
    expect(more).toBe(1); // Zed dropped past the cap
  });

  it('reports zero overflow when everything fits', () => {
    const { shown, more } = clusterSummary(['B', 'A'], 6);
    expect(shown).toEqual(['A', 'B']);
    expect(more).toBe(0);
  });

  it('ignores blank/whitespace names', () => {
    const { shown, more } = clusterSummary(['  ', '', 'Real'], 6);
    expect(shown).toEqual(['Real']);
    expect(more).toBe(0);
  });

  it('handles an empty cluster', () => {
    expect(clusterSummary([], 6)).toEqual({ shown: [], more: 0 });
  });
});
