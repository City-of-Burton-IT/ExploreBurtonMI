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

/** A toggleable GeoJSON overlay (e.g. school districts, bridges) shown via the map's
 *  layer control. Polygon/line features are styled via the `style` callback; Point
 *  features render as circle markers colored by a `_color` property (e.g. bridge
 *  condition). A feature may carry `_popupRows` ([label, value] pairs) for a
 *  multi-field popup, else `nameField` is shown. */
export interface DataLayerConfig {
  /** path (relative to the site root) to a GeoJSON FeatureCollection (polygons, lines, or points) */
  source: string;
  /** label shown in the layer-toggle control */
  label: string;
  /** feature property used as the popup label / heading (default "name") */
  nameField?: string;
}

/** A toggleable georeferenced image overlay (e.g. the zoning map) shown via the layer control. */
export interface ImageOverlayConfig {
  /** path (relative to the site root) to the image */
  source: string;
  /** label shown in the layer-toggle control */
  label: string;
  /** [[southLat, westLng], [northLat, eastLng]] geographic bounds the image is stretched to */
  bounds: [[number, number], [number, number]];
  /** image opacity 0-1 (default 0.6 so the basemap shows through) */
  opacity?: number;
  /** clip the image to the city boundary polygon (strips the out-of-city parts) */
  clipToBoundary?: boolean;
  /** path to a legend image shown in a side panel while this overlay is on */
  legend?: string;
}

export interface AppConfig {
  project: ProjectConfig;
  data: DataConfig;
  map: MapConfig;
  tiles: TilesConfig;
  /** toggleable GeoJSON overlays (off by default; user enables via a layer control) */
  dataLayers?: DataLayerConfig[];
  /** toggleable georeferenced image overlays (off by default) */
  imageOverlays?: ImageOverlayConfig[];
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
  /** listing change-request intake (#3); absent = the "Suggest an edit" UI is hidden */
  submit?: SubmitConfig;
  /** issue-report intake (#14); absent = the "Report an issue" UI is hidden */
  report?: SubmitConfig;
  /** read-only status-lookup endpoint (#status); absent = the tracking link/page is inert */
  status?: { url: string };
}

export interface SubmitConfig {
  /**
   * Power Automate HTTP-trigger URL the form posts to. The URL (incl. its SAS
   * signature) is public by design -- a static app cannot hide it, same exposure
   * as an anonymous form link. The SharePoint moderation queue is the gate.
   */
  url: string;
}

export interface SearchConfig {
  /** feature property names the fuzzy search covers */
  keys: string[];
}

// --- GeoJSON data ---------------------------------------------------------

export interface FeatureProperties {
  name: string;
  /** One category, or several when a record collapses co-located services
   *  (e.g. a big-box store with a pharmacy + auto center). The first is primary. */
  category?: string | string[];
  address?: string;
  phone?: string;
  website?: string;
  hours?: string;
  description?: string;
  /** In-store services on a collapsed big-box record (display only). */
  services?: string[];
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

export type InfoView =
  | 'finances'
  | 'fiscalhealth'
  | 'propertytax'
  | 'demographics'
  | 'schools'
  | 'health'
  | 'jobs'
  | 'environment'
  | 'water'
  | 'housing'
  | 'broadband'
  | 'bridges'
  | 'roads'
  | 'trails'
  | 'zoning'
  | 'parks'
  | 'roadsafety'
  | 'access'
  | 'seniorcenter'
  | 'publicsafety';
export type AppView = 'map' | InfoView | 'guide' | 'opendata' | 'status';

export interface InfoStat {
  label: string;
  value: string;
  /** optional small note under the value (e.g. a year or qualifier) */
  hint?: string;
  /** optional area benchmarks (e.g. Genesee County / Michigan) shown small
   *  beneath the value, so a number reads as "high or low for the area". */
  benchmarks?: { name: string; value: string }[];
  /** optional multi-decade series (e.g. decennial population) drawn as a tiny
   *  sparkline under the value. */
  spark?: { x: string; y: number }[];
}

export interface InfoSeriesItem {
  label: string;
  value: number;
  /** optional brand-palette override; falls back to the chart's default cycle */
  color?: string;
}

/** One metric compared across places (Burton vs County vs State). */
export interface CompareValue {
  name: string;
  value: number;
}
export interface CompareRow {
  label: string;
  /** unit for this metric's values ("%", "$", "" for plain) */
  unit?: string;
  values: CompareValue[];
  /** Optional "Burton vs all Genesee County cities" ranking for this metric,
   *  every city sorted high-to-low (Burton included). When present on any row,
   *  CompareBars offers a region/cities toggle. */
  cities?: CompareValue[];
}

export interface InfoChart {
  type: 'donut' | 'bars' | 'trend' | 'compare';
  title: string;
  /** unit suffix for rendered values, e.g. "$M" or "%" */
  unit?: string;
  /** donut + bars */
  series?: InfoSeriesItem[];
  /** trend line (single series) */
  points?: { x: string; y: number }[];
  /** trend: optional event markers, drawn at matching data-point x values */
  markers?: { x: string; label: string }[];
  /** trend: optional multiple series (overrides single `points` when present) */
  lines?: { label: string; points: { x: string; y: number }[]; color?: string }[];
  /** compare: one entry per metric, each holding the per-place values */
  rows?: CompareRow[];
  /** compare: optional intro shown in the cities-toggle view. When set, the
   *  cities view is framed collaboratively (this lede + no per-metric rank
   *  label); when absent, cities mode keeps the neutral "Nth highest" ranking. */
  citiesLede?: string;
}

export interface InfoLink {
  text: string;
  href: string;
}

/** One expandable concept in an interactive explainer (e.g. "What is a fund?"). */
export interface InfoExplainerItem {
  term: string;
  body: string;
}

/** An optional interactive "learn how this works" explainer for a panel: a button
 *  that reveals a set of plain-language concept cards the resident can expand. */
export interface InfoExplainer {
  /** button + heading label, e.g. "How city budgeting works" */
  title: string;
  intro?: string;
  items: InfoExplainerItem[];
  source?: string;
}

/** One school district's total tax rate (mills) for the estimator. */
export interface EstimatorDistrict {
  name: string;
  /** total mills for a homestead (owner-occupied) home */
  homestead: number;
  /** total mills for a non-homestead (rental / second home) property */
  nonHomestead: number;
}

/** Data driving the interactive property-tax estimator. The city and county
 *  millages are uniform across Burton; the school portion varies by district, so
 *  the per-district totals carry it. */
export interface InfoEstimator {
  /** City of Burton's own rate (General + Police + Fire), in mills */
  cityMills: number;
  /** Genesee County's rate, in mills (uniform countywide) */
  countyMills: number;
  districts: EstimatorDistrict[];
}

/** A plain-language "what this means for you" callout that interprets a dashboard's
 *  numbers for a resident -- what the data shows and how it affects them. Rendered as
 *  a highlighted box near the top of the panel, above the stats. */
export interface InfoSummary {
  /** callout heading (default "What this means for you") */
  heading?: string;
  /** one or more short plain-language paragraphs */
  body: string[];
}

/** One row of an InfoTable: one cell per column, plus an optional status color
 *  rendered as a leading decorative dot (e.g. a bridge's Good/Fair/Poor color). */
export interface InfoTableRow {
  cells: string[];
  color?: string;
}

/** A simple per-item table (e.g. every bridge in Burton). Cells are plain text
 *  (Svelte auto-escapes them); `columns` are the header labels in order. */
export interface InfoTable {
  title: string;
  columns: string[];
  rows: InfoTableRow[];
}

export interface InfoPanel {
  title: string;
  subtitle?: string;
  /** optional logo image (path relative to the site root) shown in the panel
   *  header, e.g. a department badge. Hidden gracefully if the file is missing. */
  logo?: string;
  /** when true, render a "not yet official" banner (finances until real figures land) */
  draft?: boolean;
  /** banner text for a draft panel; defaults to a generic "provisional" note. Use to
   *  distinguish invented mockup data ("sample") from real-but-unapproved figures
   *  ("pending department review"). */
  draftNote?: string;
  /** plain-language interpretation shown above the stats (resident "what this means") */
  summary?: InfoSummary;
  /** optional interactive "learn how this works" explainer shown after the charts */
  explainer?: InfoExplainer;
  /** optional "How we measure this" collapsible card (methodology), shown after
   *  the explainer; reuses the explainer card styling. */
  methodology?: { title?: string; body: string };
  /** optional interactive property-tax estimator (Property Taxes dashboard) */
  estimator?: InfoEstimator;
  stats: InfoStat[];
  charts: InfoChart[];
  /** optional per-item tables rendered after the charts (e.g. a bridge list) */
  tables?: InfoTable[];
  /** ISO date (YYYY-MM-DD or YYYY-MM) the data was last refreshed; rendered as a
   *  "Data as of {Month YYYY}" freshness line by the source. Often supplied via the
   *  committed freshness.json overlay rather than embedded per panel. */
  lastUpdated?: string;
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
  type: 'markdown' | 'contacts' | 'meetings' | 'waste' | 'ops-status' | 'civicclerk' | 'video';
  /** optional section icon id (see src/lib/guide/icons.ts) */
  icon?: string;
  /** video sections: the embed URL + provider label (click-to-load) */
  src?: string;
  provider?: string;
  poster?: string;
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
