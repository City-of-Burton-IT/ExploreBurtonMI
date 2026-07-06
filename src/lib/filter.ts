// Pure, DOM-free filtering + facet-count engine. This is the testable core of
// the app (unit-tested in test/filter.test.ts). Separating it from Svelte means
// the filtering logic can be reasoned about and tested without a browser - the
// deliberate improvement over Finda, where this logic was tangled in the
// event-bus components.

import type { PlaceFeature, FacetType, Facets, Selections } from './types';

export type { FacetType, FacetConfig, Facets, Selections } from './types';

/** field -> (value -> count of results if that value were selected) */
export type FacetCounts = Record<string, Record<string, number>>;

export interface FilterResult {
  filteredIds: string[];
  facetCounts: FacetCounts;
}

function valuesFor(feature: PlaceFeature, field: string): string[] {
  const v = feature.properties[field];
  if (v == null) return [];
  return Array.isArray(v) ? v.map(String) : [String(v)];
}

function matchesFacet(
  feature: PlaceFeature,
  field: string,
  selected: string[],
  type: FacetType,
): boolean {
  if (!selected.length) return true;
  const have = valuesFor(feature, field);
  if (type === 'list') {
    // feature must have ALL selected values
    return selected.every((s) => have.includes(s));
  }
  // 'single' - feature matches ANY selected value
  return selected.some((s) => have.includes(s));
}

/**
 * Compute the filtered feature IDs and live facet counts.
 *
 * Facets combine with AND across fields. Within a field, behaviour is set by the
 * facet type. `matchesExtra` is an optional predicate (used for text search in
 * M4) applied on top of the facets.
 *
 * Facet counts use the standard faceted-search rule: a value's count is how many
 * results you would get if it were selected, i.e. computed against all OTHER
 * facets' current selections (plus `matchesExtra`).
 */
export function filterFeatures(
  features: PlaceFeature[],
  facets: Facets,
  selections: Selections,
  matchesExtra: (f: PlaceFeature) => boolean = () => true,
): FilterResult {
  const fields = Object.keys(facets);

  const passesAll = (feature: PlaceFeature): boolean =>
    matchesExtra(feature) &&
    fields.every((field) =>
      matchesFacet(feature, field, selections[field] ?? [], facets[field].type),
    );

  const filteredIds = features.filter(passesAll).map((f) => f.id);

  const facetCounts: FacetCounts = {};
  for (const field of fields) {
    // base set: matches every OTHER facet + the extra predicate
    const base = features.filter(
      (feature) =>
        matchesExtra(feature) &&
        fields.every(
          (other) =>
            other === field ||
            matchesFacet(feature, other, selections[other] ?? [], facets[other].type),
        ),
    );
    const counts: Record<string, number> = {};
    for (const feature of base) {
      for (const value of valuesFor(feature, field)) {
        counts[value] = (counts[value] ?? 0) + 1;
      }
    }
    facetCounts[field] = counts;
  }

  return { filteredIds, facetCounts };
}
