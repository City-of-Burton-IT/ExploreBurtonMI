// Typed shape of public/config.json and the GeoJSON data.
// Extended per milestone as features (properties, facets, search) land.

import type { PropertyConfig } from './templates';
import type { Facets } from './filter';
export type { PropertyConfig } from './templates';

export interface ProjectConfig {
  name: string;
  tagline: string;
}

export interface DataConfig {
  source: string;
}

export interface MapConfig {
  /** [lat, lng] */
  center: [number, number];
  zoom: number;
  maxZoom: number;
  minZoom: number;
  /** [[southLat, westLng], [northLat, eastLng]] */
  maxBounds: [[number, number], [number, number]];
  /** property used as the marker hover/popup label */
  previewAttribute: string;
}

export interface TileOverlay {
  url: string;
  subdomains?: string;
}

export interface TilesConfig {
  url: string;
  attribution: string;
  subdomains?: string;
  /** transparent reference layers drawn on top of the base map (labels, roads) */
  overlays?: TileOverlay[];
}

export interface CategoryStyle {
  color: string;
}

export interface BoundaryConfig {
  /** path (relative to the site root) to a GeoJSON Feature/FeatureCollection of the city limits */
  source: string;
  /** outline stroke color */
  color?: string;
  /** outline stroke weight */
  weight?: number;
  /** tighten the map's maxBounds to the boundary extent so the view stays on the city */
  lockView?: boolean;
  /** dim the map outside the city limits (a translucent mask over everything beyond) */
  dimOutside?: boolean;
  /** mask fill color (default dark navy) */
  dimColor?: string;
  /** mask fill opacity 0–1 (default 0.5) */
  dimOpacity?: number;
}

export interface AppConfig {
  project: ProjectConfig;
  data: DataConfig;
  map: MapConfig;
  tiles: TilesConfig;
  /** property each feature is grouped/colored by */
  categoryField: string;
  /** known category values -> style; used for marker color and (later) facets */
  categories: Record<string, CategoryStyle>;
  /** optional city-limits outline drawn on the map */
  boundary?: BoundaryConfig;
  /** fields shown in the detail panel, in order, with optional formatting */
  properties: PropertyConfig[];
  /** facet definitions: field -> { title, type } */
  facets: Facets;
  /** fields shown in each sidebar list row, in order */
  list: string[];
  /** fuzzy-search configuration */
  search: SearchConfig;
}

export interface SearchConfig {
  /** feature property names the fuzzy search covers */
  keys: string[];
}

// --- GeoJSON data ---------------------------------------------------------

export interface FeatureProperties {
  name: string;
  category?: string;
  address?: string;
  phone?: string;
  website?: string;
  hours?: string;
  description?: string;
  [key: string]: unknown;
}

export interface PlaceFeature {
  type: 'Feature';
  /** stable ID assigned at load if absent */
  id: string;
  geometry: {
    type: 'Point';
    /** [lng, lat] per GeoJSON spec */
    coordinates: [number, number];
  };
  properties: FeatureProperties;
  /**
   * Curated facility whose real location is outside the city limits (e.g. a
   * permit-issued service at an out-of-town site). Listed and searchable, but
   * not plotted on the locked city map. Carries valid coordinates so the detail
   * panel's "Get directions" link still resolves.
   */
  offMap?: boolean;
}

export interface PlaceCollection {
  type: 'FeatureCollection';
  features: PlaceFeature[];
}
