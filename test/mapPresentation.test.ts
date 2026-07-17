import { describe, expect, it } from 'vitest';
import {
  businessPlace,
  filteredOutPlace,
  governmentPlace,
  mapPresentationConfig,
  missingCategoryPlace,
  offMapPlace,
  unknownCategoryPlace,
} from './fixtures/mapPlaces';
import {
  isMarkerVisible,
  isOnMapPlace,
  markerColor,
  markerStyle,
  markerTooltipHtml,
} from '../src/lib/map/presentation';

describe('map place presentation', () => {
  it('uses the configured color for a scalar category and the first array category', () => {
    expect(markerColor(governmentPlace, mapPresentationConfig)).toBe('#1f3a5f');
    expect(markerColor(businessPlace, mapPresentationConfig)).toBe('#e65100');
  });

  it('uses the neutral fallback color for missing and unknown categories', () => {
    expect(markerColor(unknownCategoryPlace, mapPresentationConfig)).toBe('#555555');
    expect(markerColor(missingCategoryPlace, mapPresentationConfig)).toBe('#555555');
  });

  it('keeps the current unselected marker style', () => {
    expect(markerStyle(governmentPlace, mapPresentationConfig)).toEqual({
      radius: 8,
      color: '#ffffff',
      weight: 1.5,
      fillColor: '#1f3a5f',
      fillOpacity: 0.9,
    });
  });

  it('uses the current selected marker style', () => {
    expect(markerStyle(governmentPlace, mapPresentationConfig, true)).toEqual({
      radius: 11,
      color: '#111111',
      weight: 3,
      fillColor: '#1f3a5f',
      fillOpacity: 0.9,
    });
  });

  it('uses the configured preview property with an escaped name fallback', () => {
    expect(markerTooltipHtml(governmentPlace, mapPresentationConfig.map.previewAttribute)).toBe(
      'City Hall &lt;Info&gt;',
    );
    expect(markerTooltipHtml(businessPlace, mapPresentationConfig.map.previewAttribute)).toBe('Burton Diner');
  });

  it('creates map markers only for on-map places and hides filtered-out markers', () => {
    const visibleIds = new Set([governmentPlace.id, businessPlace.id]);

    expect(isOnMapPlace(governmentPlace)).toBe(true);
    expect(isOnMapPlace(offMapPlace)).toBe(false);
    expect(isMarkerVisible(governmentPlace, visibleIds)).toBe(true);
    expect(isMarkerVisible(filteredOutPlace, visibleIds)).toBe(false);
  });
});

