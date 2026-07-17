import type { AppConfig, PlaceFeature } from '../types';
import { escapeHtml } from './html';

export interface MarkerStyle {
  radius: number;
  color: string;
  weight: number;
  fillColor: string;
  fillOpacity: number;
}

type CategoryConfig = Pick<AppConfig, 'categoryField' | 'categories'>;

const DEFAULT_COLOR = '#555555';

export function markerColor(feature: PlaceFeature, config: CategoryConfig): string {
  const raw = feature.properties[config.categoryField];
  const category = (Array.isArray(raw) ? raw[0] : raw) as string | undefined;
  return (category && config.categories[category]?.color) || DEFAULT_COLOR;
}

export function markerStyle(
  feature: PlaceFeature,
  config: CategoryConfig,
  selected = false,
): MarkerStyle {
  return {
    radius: selected ? 11 : 8,
    color: selected ? '#111111' : '#ffffff',
    weight: selected ? 3 : 1.5,
    fillColor: markerColor(feature, config),
    fillOpacity: 0.9,
  };
}

export function markerTooltipHtml(feature: PlaceFeature, previewAttribute: string): string {
  return escapeHtml(String(feature.properties[previewAttribute] ?? feature.properties.name));
}

export function isOnMapPlace(feature: PlaceFeature): boolean {
  return !feature.offMap;
}

export function isMarkerVisible(feature: PlaceFeature, filteredIds: Set<string>): boolean {
  return isOnMapPlace(feature) && filteredIds.has(feature.id);
}

