// Thin wrapper around MiniSearch for client-side search over the dataset.
// MiniSearch is token/prefix based (matches whole search terms with optional
// prefix + light typo tolerance), which gives predictable "contains this word"
// results for a civic directory - unlike character-level fuzzy matching, which
// produced noisy matches (e.g. "park" -> "Police Department").

import MiniSearch from 'minisearch';
import type { PlaceFeature } from './types';

export type SearchIndex = MiniSearch<PlaceFeature>;

export function buildIndex(features: PlaceFeature[], keys: string[]): SearchIndex {
  const index = new MiniSearch<PlaceFeature>({
    fields: keys,
    idField: 'id',
    extractField: (doc, field) => {
      if (field === 'id') return doc.id;
      const v = doc.properties[field];
      if (v == null) return '';
      return Array.isArray(v) ? v.join(' ') : String(v);
    },
  });
  index.addAll(features);
  return index;
}

/**
 * Return the set of matching feature IDs for a query, or null for an empty
 * query (null means "no search active" - do not filter on search).
 */
export function searchIds(index: SearchIndex, query: string): Set<string> | null {
  const q = query.trim();
  if (q.length < 2) return null;
  const results = index.search(q, { prefix: true, fuzzy: 0.2, combineWith: 'AND' });
  return new Set(results.map((r) => r.id as string));
}
