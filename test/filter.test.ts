import { describe, it, expect } from 'vitest';
import { filterFeatures, type Facets } from '../src/lib/filter';
import type { PlaceFeature, FeatureProperties } from '../src/lib/types';

function feature(id: string, props: FeatureProperties): PlaceFeature {
  return {
    type: 'Feature',
    id,
    geometry: { type: 'Point', coordinates: [0, 0] },
    properties: props,
  };
}

const features: PlaceFeature[] = [
  feature('a', { name: 'A', category: 'Government', tags: ['x', 'y'] }),
  feature('b', { name: 'B', category: 'Public Safety', tags: ['x'] }),
  feature('c', { name: 'C', category: 'Public Safety', tags: ['y'] }),
  feature('d', { name: 'D', category: 'Parks', tags: ['x', 'y', 'z'] }),
];

const facets: Facets = {
  category: { title: 'Category', type: 'single' },
  tags: { title: 'Tags', type: 'list' },
};

describe('filterFeatures', () => {
  it('returns all features when nothing is selected', () => {
    const r = filterFeatures(features, facets, {});
    expect(r.filteredIds).toEqual(['a', 'b', 'c', 'd']);
  });

  it('single facet matches ANY selected value', () => {
    const r = filterFeatures(features, facets, { category: ['Public Safety'] });
    expect(r.filteredIds).toEqual(['b', 'c']);
  });

  it('single facet with multiple values is a union', () => {
    const r = filterFeatures(features, facets, { category: ['Government', 'Parks'] });
    expect(r.filteredIds).toEqual(['a', 'd']);
  });

  it('list facet matches ALL selected values', () => {
    const r = filterFeatures(features, facets, { tags: ['x', 'y'] });
    expect(r.filteredIds).toEqual(['a', 'd']); // both have x AND y
  });

  it('combines facets with AND across fields', () => {
    const r = filterFeatures(features, facets, {
      category: ['Public Safety'],
      tags: ['y'],
    });
    expect(r.filteredIds).toEqual(['c']); // Public Safety AND has tag y
  });

  it('computes facet counts independent of that facet\'s own selection', () => {
    const r = filterFeatures(features, facets, { category: ['Public Safety'] });
    // category counts ignore the category selection itself -> full distribution
    expect(r.facetCounts.category).toEqual({
      Government: 1,
      'Public Safety': 2,
      Parks: 1,
    });
    // tag counts are constrained to the selected category (b, c)
    expect(r.facetCounts.tags).toEqual({ x: 1, y: 1 });
  });

  it('applies the matchesExtra predicate (e.g. search)', () => {
    const onlyAandC = (f: PlaceFeature) => f.id === 'a' || f.id === 'c';
    const r = filterFeatures(features, facets, {}, onlyAandC);
    expect(r.filteredIds).toEqual(['a', 'c']);
    // counts also reflect the predicate
    expect(r.facetCounts.category).toEqual({ Government: 1, 'Public Safety': 1 });
  });
});
