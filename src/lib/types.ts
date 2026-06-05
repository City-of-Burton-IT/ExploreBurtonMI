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

/** A toggleable GeoJSON overlay (e.g. school districts) shown via the map's layer control. */
export interface DataLayerConfig {
  /** path (relative to the site root) to a GeoJSON FeatureCollection of polygons */
  source: string;
  /** label shown in the layer-toggle control */
  label: string;
  /** feature property used as the hover label (default "name") */
  nameField?: string;
}

export interface AppConfig {
  project: ProjectConfig;
  data: DataConfig;
  map: MapConfig;
  tiles: TilesConfig;
  /** toggleable GeoJSON overlays (off by default; user enables via a layer control) */
  dataLayers?: DataLayerConfig[];
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

// --- Info panels (Finances / Demographics) --------------------------------
// Resident-facing snapshot views, each driven by a committed JSON file. No PII;
// display-only public data, so they live outside the map's public-safe gate.

export type InfoView = 'finances' | 'demographics';
export type AppView = 'map' | InfoView | 'guide';

export interface InfoStat {
  label: string;
  value: string;
  /** optional small note under the value (e.g. a year or qualifier) */
  hint?: string;
}

export interface InfoSeriesItem {
  label: string;
  value: number;
  /** optional brand-palette override; falls back to the chart's default cycle */
  color?: string;
}

export interface InfoChart {
  type: 'donut' | 'bars' | 'trend';
  title: string;
  /** unit suffix for rendered values, e.g. "$M" or "%" */
  unit?: string;
  /** donut + bars */
  series?: InfoSeriesItem[];
  /** trend line */
  points?: { x: string; y: number }[];
}

export interface InfoLink {
  text: string;
  href: string;
}

export interface InfoPanel {
  title: string;
  subtitle?: string;
  /** when true, render a "not yet official" banner (finances until real figures land) */
  draft?: boolean;
  stats: InfoStat[];
  charts: InfoChart[];
  source?: string;
  links?: InfoLink[];
  /** small footnotes under the source line (data caveats, required attributions) */
  notes?: string[];
}

// --- Resident Guide -------------------------------------------------------
// Built from content/guide/* by tools/build_guide.mjs into public/guide.json.
// Display-only public data (city-published); no resident PII.

export interface GuideSectionMeta {
  id: string;
  title: string;
  type: 'markdown' | 'contacts' | 'meetings';
}

export interface GuidePerson {
  title: string;
  name: string;
  phone?: string;
  email?: string;
  committees?: string[];
}

export interface GuideContacts {
  groups: { name: string; people: GuidePerson[] }[];
}

export interface GuideMeeting {
  /** ISO YYYY-MM-DD */
  date: string;
  time: string;
  /** moved for a holiday/election */
  alt?: boolean;
}

export interface GuideMeetings {
  intro?: string;
  council: GuideMeeting[];
  boards: { name: string; schedule: string }[];
}

export interface GuideBundle {
  sections: GuideSectionMeta[];
  pdf?: string;
  /** rendered HTML for markdown sections, keyed by section id */
  content: Record<string, string>;
  contacts?: GuideContacts;
  meetings?: GuideMeetings;
}
