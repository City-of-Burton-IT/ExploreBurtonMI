// Shared reactive app state (Svelte 5 runes in a .svelte.ts module).
// Keeps cross-component state (selection + facet selections) in one place so
// Map, List, and Facets stay in sync without prop-drilling.

import type { PlaceFeature, AppView, InfoView } from './types';
import type { Selections } from './filter';
import { placeIdFromHash, placeHash } from './hash';

export interface DashboardItem {
  id: InfoView;
  label: string;
  /** optional one-line plain-language description: a sub-line in the menu and a
   *  subtitle fallback on the panel. Interim wording -- resident-tested copy is
   *  finalized (with city approval) in issue #38. */
  description?: string;
}
export interface DashboardGroup {
  label: string;
  items: DashboardItem[];
}

/** Dashboards organized into themed groups -- the single source of truth for the
 *  grouped menu, hash routing, and which panels to load. Add a dashboard by
 *  placing it in the right group; everything else derives from this. */
export const DASHBOARD_GROUPS: DashboardGroup[] = [
  {
    label: 'People & Housing',
    items: [
      { id: 'demographics', label: 'Demographics', description: 'Population, age, and household trends from the U.S. Census.' },
      { id: 'jobs', label: 'Jobs & Employers', description: 'Where residents work, top employers, and commuting.' },
      { id: 'access', label: 'Affordability & Access', description: 'Cost of living, income, and transportation access.' },
      { id: 'housing', label: 'Housing & Growth', description: 'Homes, ownership, values, and how housing has grown.' },
      { id: 'zoning', label: 'Zoning', description: 'How land across the city is zoned and used.' },
      { id: 'schools', label: 'Schools', description: 'Public school districts serving Burton and outcomes.' },
    ],
  },
  {
    label: 'Money & Taxes',
    items: [
      { id: 'finances', label: 'City Finances', description: 'How the city raises and spends money each year.' },
      { id: 'propertytax', label: 'Property Taxes', description: 'What makes up your property tax bill and where it goes.' },
      { id: 'fiscalhealth', label: 'Financial Health', description: "The city's debt, pensions, and long-term outlook." },
    ],
  },
  {
    label: 'Health & Environment',
    items: [
      { id: 'health', label: 'Community Health', description: 'Health indicators and how Burton compares.' },
      { id: 'water', label: 'Drinking Water', description: 'Your water source, quality, and safety record.' },
      { id: 'environment', label: 'Environment', description: 'Air quality and environmental measures.' },
      { id: 'parks', label: 'Parks', description: 'City and county parks, acreage, and upkeep.' },
      { id: 'trails', label: 'Trails & Pathways', description: 'Walking and biking trails across the city.' },
      { id: 'seniorcenter', label: 'Senior Center', description: 'Programs, activity, and services for seniors.' },
    ],
  },
  {
    label: 'Infrastructure',
    items: [
      { id: 'broadband', label: 'Broadband Access', description: 'Internet providers, speeds, and coverage.' },
      { id: 'bridges', label: 'Bridges & Infrastructure', description: 'Condition and traffic of every bridge in the city.' },
      { id: 'roads', label: 'Roads & Pavement', description: 'Pavement condition of the federal-aid road network.' },
    ],
  },
  {
    label: 'Public Safety',
    items: [
      { id: 'publicsafety', label: 'Burton Fire & Rescue', description: 'Fire & Rescue calls, response, and trends.' },
      { id: 'roadsafety', label: 'Roadway Safety', description: 'Where and how often traffic crashes happen (historical).' },
    ],
  },
];

/** Flat list (display order) derived from the groups -- used by hash routing,
 *  panel loading, and the active-dashboard lookup. */
export const DASHBOARDS: DashboardItem[] = DASHBOARD_GROUPS.flatMap((g) => g.items);

const DASHBOARD_IDS = new Set<string>(DASHBOARDS.map((d) => d.id));

/** True when a view is one of the dashboard info-panels. */
export function isDashboard(view: AppView): view is InfoView {
  return DASHBOARD_IDS.has(view);
}

/** The themed-group label containing a dashboard (e.g. "Money & Taxes"), or null. */
export function dashboardGroupLabel(id: AppView): string | null {
  for (const g of DASHBOARD_GROUPS) if (g.items.some((d) => d.id === id)) return g.label;
  return null;
}

/** The dashboards before/after a given one in the flat display order (for prev/next). */
export function adjacentDashboards(id: AppView): {
  prev: DashboardItem | null;
  next: DashboardItem | null;
} {
  const i = DASHBOARDS.findIndex((d) => d.id === id);
  if (i < 0) return { prev: null, next: null };
  return { prev: DASHBOARDS[i - 1] ?? null, next: DASHBOARDS[i + 1] ?? null };
}

/** Map a URL hash (#finances, #guide, #guide/trash) to a top-level view. */
export function viewFromHash(hash: string): AppView {
  const key = hash.replace(/^#/, '').split('/')[0];
  if (key === 'guide' || DASHBOARD_IDS.has(key)) return key as AppView;
  return 'map';
}

/** The guide section id from a `#guide/<id>` hash, or null. */
export function guideSectionFromHash(hash: string): string | null {
  const parts = hash.replace(/^#/, '').split('/');
  return parts[0] === 'guide' && parts[1] ? parts[1] : null;
}

function initialView(): AppView {
  return typeof window === 'undefined' ? 'map' : viewFromHash(window.location.hash);
}

function initialGuideSection(): string | null {
  return typeof window === 'undefined' ? null : guideSectionFromHash(window.location.hash);
}

export const ui = $state<{
  selected: PlaceFeature | null;
  selections: Selections;
  query: string;
  /** which pane is shown on narrow (phone/tablet) screens */
  mobileView: 'map' | 'list';
  /** whether the About dialog is open */
  aboutOpen: boolean;
  /** top-level section: the map, an info panel, or the guide */
  view: AppView;
  /** active Resident Guide section id (null = the guide's first section) */
  guideSection: string | null;
  /** the user's location once they tap "Near me" (drives map centering + list sort) */
  userLocation: { lat: number; lng: number } | null;
  /** true once the browser signals the PWA can be installed (Android/desktop) */
  canInstall: boolean;
}>({
  selected: null,
  selections: {},
  query: '',
  mobileView: 'map',
  aboutOpen: false,
  view: initialView(),
  guideSection: initialGuideSection(),
  userLocation: null,
  canInstall: false,
});

/** Record (or clear) the user's location after a "Near me" request. */
export function setUserLocation(loc: { lat: number; lng: number } | null): void {
  ui.userLocation = loc;
}

// --- PWA install -----------------------------------------------------------
// The browser fires `beforeinstallprompt` (Android/desktop Chromium) once the app
// is installable; we stash it so an in-app button can trigger the native prompt on
// demand. iOS has no such event -- the component shows a manual hint instead.
export interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

let deferredInstallPrompt: BeforeInstallPromptEvent | null = null;

/** Called from main.ts when the browser offers an install. */
export function captureInstallPrompt(e: BeforeInstallPromptEvent): void {
  deferredInstallPrompt = e;
  ui.canInstall = true;
}

/** Fire the stored native install prompt (Android/desktop). */
export async function triggerInstall(): Promise<void> {
  if (!deferredInstallPrompt) return;
  await deferredInstallPrompt.prompt();
  await deferredInstallPrompt.userChoice;
  deferredInstallPrompt = null;
  ui.canInstall = false;
}

/** Called when the app has been installed (clears any install UI). */
export function markInstalled(): void {
  deferredInstallPrompt = null;
  ui.canInstall = false;
}

/** Switch the top-level view and reflect it in the URL hash (shareable + Back). */
export function setView(view: AppView): void {
  ui.view = view;
  if (typeof window === 'undefined') return;
  if (view === 'map') {
    if (window.location.hash) {
      history.pushState(null, '', window.location.pathname + window.location.search);
    }
  } else if (viewFromHash(window.location.hash) !== view) {
    window.location.hash = view;
  }
}

/** Select a Resident Guide section and reflect it in the hash (#guide/<id>). */
export function setGuideSection(id: string): void {
  ui.view = 'guide';
  ui.guideSection = id;
  if (typeof window !== 'undefined') window.location.hash = `guide/${id}`;
}

/** Sync the view (+ guide section) from the current hash (Back/Forward + deep links). */
export function syncViewFromHash(): void {
  const hash = typeof window === 'undefined' ? '' : window.location.hash;
  ui.view = viewFromHash(hash);
  ui.guideSection = guideSectionFromHash(hash);
}

export function setMobileView(view: 'map' | 'list'): void {
  ui.mobileView = view;
}

export function openAbout(): void {
  ui.aboutOpen = true;
}

export function closeAbout(): void {
  ui.aboutOpen = false;
}

export function select(feature: PlaceFeature | null): void {
  ui.selected = feature;
  if (feature) {
    // Picking a place reveals it on the map (+ its detail sheet) and makes the
    // URL a shareable permalink (#map/place/<id>). The id-equality guard means
    // applying a place from the hash re-writes the same value -> no event loop.
    ui.mobileView = 'map';
    ui.view = 'map';
    if (typeof window !== 'undefined') {
      const h = placeHash(feature.id);
      if (window.location.hash.replace(/^#/, '') !== h) window.location.hash = h;
    }
  }
}

export function clearSelection(): void {
  ui.selected = null;
  // Drop the place from the URL (keep the clean map URL) without a history entry.
  if (typeof window !== 'undefined' && placeIdFromHash(window.location.hash)) {
    history.replaceState(null, '', window.location.pathname + window.location.search);
  }
}

/** Add or remove a value from a facet field's selection. */
export function toggleFacet(field: string, value: string): void {
  const current = ui.selections[field] ?? [];
  const next = current.includes(value)
    ? current.filter((v) => v !== value)
    : [...current, value];
  ui.selections = { ...ui.selections, [field]: next };
}

/** Clear all selected values for one facet field. */
export function clearFacet(field: string): void {
  ui.selections = { ...ui.selections, [field]: [] };
}
