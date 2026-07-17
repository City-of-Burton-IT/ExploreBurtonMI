import type { AppConfig, PlaceFeature } from '../../src/lib/types';

export const mapPresentationConfig = {
  categoryField: 'category',
  categories: {
    Government: { color: '#1f3a5f' },
    Dining: { color: '#e65100' },
  },
  map: { previewAttribute: 'mapLabel' },
} as Pick<AppConfig, 'categoryField' | 'categories' | 'map'>;

export const governmentPlace: PlaceFeature = {
  type: 'Feature',
  id: 'city-hall',
  geometry: { type: 'Point', coordinates: [-83.632, 43.002] },
  properties: { name: 'Burton City Hall', category: 'Government', mapLabel: 'City Hall <Info>' },
};

export const businessPlace: PlaceFeature = {
  type: 'Feature',
  id: 'burton-diner',
  geometry: { type: 'Point', coordinates: [-83.63, 43.001] },
  properties: { name: 'Burton Diner', category: ['Dining', 'Community Services'] },
};

export const unknownCategoryPlace: PlaceFeature = {
  type: 'Feature',
  id: 'uncategorized',
  geometry: { type: 'Point', coordinates: [-83.631, 43.003] },
  properties: { name: 'Uncategorized Place', category: 'Unlisted' },
};

export const missingCategoryPlace: PlaceFeature = {
  type: 'Feature',
  id: 'missing-category',
  geometry: { type: 'Point', coordinates: [-83.633, 43.003] },
  properties: { name: 'Missing Category Place' },
};

export const offMapPlace: PlaceFeature = {
  type: 'Feature',
  id: 'outside-burton',
  geometry: { type: 'Point', coordinates: [-83.8, 42.8] },
  properties: { name: 'List Only Place', category: 'Government' },
  offMap: true,
};

export const filteredOutPlace: PlaceFeature = {
  type: 'Feature',
  id: 'filtered-out',
  geometry: { type: 'Point', coordinates: [-83.634, 43.004] },
  properties: { name: 'Filtered Out Place', category: 'Dining' },
};

